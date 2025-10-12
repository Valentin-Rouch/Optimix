from librairies import *

THIS_DIR = Path(__file__).resolve().parent
CONSTRAINTS_PATH = THIS_DIR / "asset_class.xlsx"
asset_class = pd.read_excel(CONSTRAINTS_PATH)

def get_Q(df):
    Q = pd.to_numeric(df["pourcentage"]) / 100.0
    return Q

def get_P(views, asset_class, inst_list):
    P = pd.DataFrame(0.0, index=range(len(views)), columns=inst_list)
    asset_class = asset_class[asset_class["Asset"].isin(inst_list)]
    def group_weights(col_name, group_value):
        mask = asset_class[col_name] == group_value
        tickers = asset_class.loc[mask, "Asset"]
        if tickers.empty:
            raise ValueError(f"Aucun actif trouvé pour {col_name} == {group_value}")
        w = pd.Series(1.0 / len(tickers), index=tickers.values)
        w.index.name = None
        return w

    for i, row in views.reset_index(drop=True).iterrows():
        set_name = row["Set"]
        position = row["Position"]
        rel = row.get("Relative", "")

        w_pos = group_weights(set_name, position)
        P.loc[i, w_pos.index] += w_pos.values

        if isinstance(rel, str) and rel: # isinstance verifie que rel est un str et non vide. Ce qui implique qu'on considère ici le cas des vues relatives
            w_rel = group_weights(set_name, rel)
            P.loc[i, w_rel.index] -= w_rel.values

    return P

def get_omega(tau, P, sigma):
    # Conversion en arrays numpy
    if isinstance(P, pd.DataFrame):
        P_values = P.values
    else:
        P_values = np.asarray(P)
        
    if isinstance(sigma, pd.DataFrame):
        sigma_values = sigma.values
    else:
        sigma_values = np.asarray(sigma)
    
    k = P_values.shape[0]  # nombre de vues
    omega_diag = np.zeros(k)

    # Boucle sur les vues
    for i in range(k):
        p_i = P_values[i, :].reshape(1, -1)
        omega_diag[i] = p_i @ (tau * sigma_values) @ p_i.T
    
    omega = np.diag(omega_diag)
    return omega

