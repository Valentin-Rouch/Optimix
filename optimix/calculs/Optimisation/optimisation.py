from librairies import *
from data_access.sql_loader import load_sql

THIS_DIR = Path(__file__).resolve().parent
CONSTRAINTS_PATH = THIS_DIR / "constraints.xlsx"
contraints_df = pd.read_excel(CONSTRAINTS_PATH)

def get_matrix_contraintes(inst_list, constraints_df, exposure_df, id_fund, col_bsup, col_binf, expo_col_bsup, expo_col_binf):
    # 1) isole la ligne du fonds
    row_df = constraints_df.loc[constraints_df["id_fund"] == id_fund]
    row = row_df.squeeze()

    # 2) sanity checks d’alignement par position
    if len(col_bsup) != len(expo_col_bsup):
        raise ValueError("col_bsup et expo_col_bsup doivent avoir la même longueur.")
    if len(col_binf) != len(expo_col_binf):
        raise ValueError("col_binf et expo_col_binf doivent avoir la même longueur.")

    # 3) Aligner ET typer uniquement les colonnes utilisées
    cols_needed = set(expo_col_bsup) | set(expo_col_binf)
    cols_needed = list(cols_needed)
    expo = (exposure_df
            .set_index("id_inst")
            .loc[inst_list, cols_needed]   # même ordre que w
            .fillna(0.0)
            .astype(float)) 

    A_blocks, b_blocks = [], []

    # 4) bornes sup :  (w * expo[col]) <= ub
    if len(col_bsup) > 0:
        A_sup = sp.csr_matrix(np.vstack([expo[c].to_numpy() for c in expo_col_bsup]))
        b_sup = row[col_bsup].to_numpy(dtype=float)
        A_blocks.append(A_sup); b_blocks.append(b_sup)

    # 5) bornes inf :  (w * expo[col]) >= lb  <=>  -(w * expo[col]) <= -lb
    if len(col_binf) > 0:
        A_inf = sp.csr_matrix(np.vstack([(-expo[c].to_numpy()) for c in expo_col_binf]))
        b_inf = -row[col_binf].to_numpy(dtype=float)
        A_blocks.append(A_inf); b_blocks.append(b_inf)

    A = sp.vstack(A_blocks, format="csr")
    b = np.concatenate(b_blocks)
    return A, b

def get_cvxpy_contraintes(constraints_df, exposure_df, id_fund, A, b, inst_list):
    contraintes = []
    w = cp.Variable(len(inst_list))
    z = cp.Variable(len(inst_list), boolean=True)
    cash = cp.Variable(nonneg=True)

    min_weight = constraints_df.loc[constraints_df["id_fund"] == id_fund, "min_weight_inst"].iloc[0]
    max_weight = constraints_df.loc[constraints_df["id_fund"] == id_fund, "max_weight_inst"].iloc[0]
    max_vec = np.full(len(inst_list), max_weight, dtype=float)
    if id_fund == 65 and 426 in inst_list:
        max_vec[inst_list.index(426)] = 0.79
    elif id_fund == 66 and 344 in inst_list:
        max_vec[inst_list.index(344)] = 0.79

    contraintes += [cp.sum(w) + cash == 1.0, cash <= 0.10]
    contraintes += [-w <= -min_weight*z, w <= cp.multiply(max_vec, z), -w <= 0] # Contrainte sur les poids min et max de chaque instrument
    contraintes += [A @ w <= b] # Toutes les contraintes vertes et bleues
    
    if constraints_df.loc[constraints_df["id_fund"] == id_fund, "min_ss_jacent_UCITS"].iloc[0] == 1:
        contraintes += [-cp.sum(cp.multiply(w, exposure_df["is_ucits"])) <= (cash - constraints_df.loc[constraints_df["id_fund"] == id_fund, "min_ss_jacent_UCITS"].iloc[0])]
    else:
        contraintes += [-cp.sum(cp.multiply(w, exposure_df["is_ucits"])) <= -constraints_df.loc[constraints_df["id_fund"] == id_fund, "min_ss_jacent_UCITS"].iloc[0]]

    if constraints_df.loc[constraints_df["id_fund"] == id_fund, "min_sdg_natixis"].iloc[0] == 1:
        contraintes += [-cp.sum(cp.multiply(w, exposure_df["is_sdg_natixis"])) <= (cash - constraints_df.loc[constraints_df["id_fund"] == id_fund, "min_sdg_natixis"].iloc[0])]
    else:
        contraintes += [-cp.sum(cp.multiply(w, exposure_df["is_sdg_natixis"])) <= -constraints_df.loc[constraints_df["id_fund"] == id_fund, "min_sdg_natixis"].iloc[0]]

    return contraintes, w, cash

def get_optimisation(inst_list, contraintes, w, cash, delta, mu_bl, sigma_bl):
    delta = delta
    ret = mu_bl.T @ w
    risk = cp.quad_form(w, sigma_bl, assume_PSD=True)
    objective = cp.Maximize(ret - (delta/2) * risk)
    prob = cp.Problem(objective, contraintes)

    prob.solve(solver=cp.SCIP, verbose=False)

    inst_nm_list = load_sql(f"SELECT id_inst, nm_inst FROM AssetDescription")
    inst_nm_list = inst_nm_list[inst_nm_list["id_inst"].isin(inst_list)]

    weights_df = pd.DataFrame({"id_inst": inst_nm_list["id_inst"], "nm_inst": inst_nm_list["nm_inst"], "weight": w.value})
    weights_df["weight"] = (weights_df["weight"] * 100).round(2)
    weights_df = weights_df[weights_df["weight"] != 0]
    return weights_df, cash.value