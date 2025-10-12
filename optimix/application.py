from librairies import *
from styles import *

ROOT = Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from data_access.sql_loader import load_sql
from optimix.calculs.Black_Litterman_Model.data_collection  import get_inst_data
from optimix.calculs.Black_Litterman_Model.market_model  import get_delta_and_weights, get_cov_matrix, get_pi, psd_projection
from optimix.calculs.Black_Litterman_Model.view_model.view_model  import get_Q, get_P, get_omega, asset_class
from optimix.calculs.Black_Litterman_Model.merging_model  import get_BL
from optimix.calculs.Optimisation.optimisation import get_matrix_contraintes, get_cvxpy_contraintes, get_optimisation, contraints_df
from optimix.calculs.Optimisation.funds_of_interest import fund_list

def mapping_fund():
    mapping = load_sql(f"SELECT id_fund, nm_fund FROM AumDescription")
    mapping = mapping[mapping["id_fund"].isin(fund_list)]
    mapping = dict(zip(mapping["nm_fund"], mapping["id_fund"]))
    return mapping

fonds_dict = mapping_fund()
fund_names = sorted(fonds_dict.keys())
default_fund_name = fund_names[0] if fund_names else None
'''theme_options = list(asset_class.columns)[3:]
theme_options = [{"label": c, "value": c} for c in theme_options]'''

def options_for_theme(theme: str, inst_list):
    if not theme or theme not in asset_class.columns:
        return []
    ac = asset_class.copy()
    try:
        mask = ac["Asset"].astype(int).isin(inst_list)
    except Exception:
        mask = ac["Asset"].astype(str).isin(inst_list)
    vals = ac.loc[mask, theme].dropna().astype(str).unique().tolist()
    vals.sort()
    return [{"label": v, "value": v} for v in vals]

def date_formating(value):
    """
    value peut être une str 'YYYY-MM-DD' (Dash) ou un objet date/datetime.
    Retourne (yyyymmdd, dd_mm_yyyy) en chaînes.
    """
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
    elif isinstance(value, (datetime, date)):
        dt = value if isinstance(value, datetime) else datetime.combine(value, datetime.min.time())
    else:
        raise ValueError(f"Format de date inattendu: {type(value)}")

    return dt.strftime("%Y%m%d"), dt.strftime("%d-%m-%Y")



# App Dash
app = dash.Dash(
    __name__,
    title="Optimix",
    assets_folder="../assets"
)

# Layout
app.layout = html.Div(
    [
        # Header
        html.Div(
            [
                html.H1("Optimix", style=header_title_style),
                html.Img(src="/assets/eres_logo.png", style=header_logo_style),
            ],
            style=header_container_style,
        ),
        # Colonne gauche : dropdown (empilés, alignés à gauche)
        dcc.Store(id="inst-list-store", data=[]),
        dcc.Store(id="market-store", data={}),
        dcc.Store(id="inst-exposure-store", data={}),
        html.Div(
            [
            html.Div(
                [
                    html.Label("Choisir un fonds :", style=label_style),
                    dcc.Dropdown(
                        id="fonds-dropdown",
                        options=[{"label": name, "value": name} for name in fund_names],
                        value=default_fund_name,
                        className="dropdown",
                        style=dropdown_style,
                    ),
                ],
                style={"minWidth": "360px", "flex": "1"},
                ),
            html.Div(
                [
                    html.Label("Date de prise en compte", style=label_style),
                    dcc.DatePickerSingle(
                        id="start-date",
                        date=date(2022, 9, 10),          # valeur par défaut
                        min_date_allowed=date(2010, 1, 1),
                        max_date_allowed=date.today(),
                        display_format="DD-MM-YYYY",
                        placeholder="DD-MM-YYYY",
                    ),
                ],
                style={"minWidth": "360px", "flex": "1"},
                ),
            html.Div(
                [
                    html.Label("Tau (τ) — en %", style=label_style),
                    dcc.Input(
                        id="tau-input",
                        type="number",
                        min=2.5,
                        max=5,
                        step=0.1,
                        value=2.5,
                        debounce=True,    # calcule seulement quand l'utilisateur valide
                        style={**dropdown_style, "height": "38px"},
                    ),
                ],
                style={"minWidth": "180px", "flex": "0 0 200px"},
                ),
        ],
        style={"display": "flex", "gap": "16px", "alignItems": "flex-end", "marginTop": "8px"},
        ),
# Résumé sous le dropdown des fonds
        dcc.Loading(
            id="inst-loading",
            type="default",
            parent_className="loading-wrap",
            children=html.Div(id="inst-summary", style={"marginTop": "6px"})),
        html.Div(
            [
                html.H2("Vues des gérants", style=label_style if "section_title_style" in globals() else {}),
                dcc.Store(id="views-store", data=[]),
            # Ligne = 1 vue
            html.Div(
                [
                    # 1) Thème (colonne de asset_class.xlsx)
                    html.Div(
                        [
                            html.Label("Thème", style=label_style),
                            dcc.Dropdown(
                                id="theme-dd",
                                options=[],
                                placeholder="Choisir un thème",
                                className="dropdown",
                                style=dropdown_style,
                            ),
                        ],
                        style={"minWidth": "220px"},
                    ),

                    # 2) Élément 1
                    html.Div(
                        [
                            html.Label("Élément 1", style=label_style),
                            dcc.Dropdown(
                                id="value1-dd",
                                options=[],
                                placeholder="Choisir l’élément 1",
                                className="dropdown",
                                style=dropdown_style,
                            ),
                        ],
                        style={"minWidth": "220px"},
                    ),

                    # 3) Signe >=
                    html.Div(
                        [
                            html.Label(" ", style={**label_style, "visibility": "hidden"}),
                            html.Div("≥", style={"fontSize": "24px", "paddingTop": "6px", "textAlign": "center"}),
                        ],
                        style={"width": "40px"},
                    ),

                    # 4) Élément 2
                    html.Div(
                        [
                            html.Label("Élément 2", style=label_style),
                            dcc.Dropdown(
                                id="value2-dd",
                                options=[],
                                placeholder="Choisir l’élément 2",
                                className="dropdown",
                                style=dropdown_style,
                            ),
                        ],
                        style={"minWidth": "220px"},
                    ),

                    # 5) % de surperformance
                    html.Div(
                        [
                            html.Label("% surperformance", style=label_style),
                            dcc.Input(
                                id="pct-input",
                                type="number",
                                placeholder="ex: 3 (pour 3%)",
                                debounce=True,
                                style={**dropdown_style, "height": "38px"},
                            ),
                        ],
                        style={"minWidth": "220px"},
                    ),

                    # Bouton d’ajout
                    html.Div(
                        [
                            html.Label(" ", style={**label_style, "visibility": "hidden"}),
                            html.Button("Ajouter la vue", id="add-view-btn", n_clicks=0, className="btn"),
                        ],
                    ),
                ],
                style={"display": "grid", "gridTemplateColumns": "220px 220px 40px 220px 220px 1fr", "gap": "12px"},
            ),

            # Tableau récapitulatif des vues
            html.Div(
                [
                    html.H3("Vues saisies"),
                    dash_table.DataTable(
                        id="views-table",
                        columns=[
                            {"name": "Thème", "id": "theme"},
                            {"name": "Élément 1", "id": "value1"},
                            {"name": "Opérateur", "id": "op"},
                            {"name": "Élément 2", "id": "value2"},
                            {"name": "Pourcentage", "id": "pourcentage"},
                        ],
                        data=[],
                        page_size=8,
                        row_deletable=True,
                        editable=True,
                        style_table={"overflowX": "auto"},
                        style_cell={"fontFamily": "inherit", "fontSize": "0.9rem"},
                    ),
                ],
                style={"marginTop": "16px"},
            ),
        ],
        style={"marginTop": "24px"},
    ),
        html.Div(
        [
            html.H2("Optimisation Black–Litterman", style=label_style if "section_title_style" in globals() else {}),
            html.Div(
                [
                    html.Button("Optimiser", id="run-optim-btn", n_clicks=0, className="btn"),
                    html.Div(id="optim-msg", style={"marginLeft": "12px", "alignSelf": "center"}),
                ],
                style={"display": "flex", "gap": "12px", "marginTop": "12px"},
            ),
            dcc.Loading(
                id="optim-loading",
                type="default",
                children=html.Div(
                    dash_table.DataTable(
                        id="optim-results",
                        columns=[],
                        data=[],
                        page_size=12,
                        style_table={"overflowX": "auto", "marginTop": "16px"},
                        style_cell={"fontFamily": "inherit", "fontSize": "0.9rem"},
                    )
                ),
            ),
        ],
        style={"marginTop": "24px"},
    ),
    ],
    className="main-container",
)


# Callbacks
@app.callback(
    Output("inst-list-store", "data"),
    Output("market-store", "data"),
    Output("inst-summary", "children"),
    Output("inst-exposure-store", "data"),
    Input("start-date", "date"),
    prevent_initial_call=False,
)
def build_universe_and_market(start_date_str):
    if not start_date_str:
        return [], {}, "Aucune date sélectionnée.", {}

    try:
        # 1) Univers
        yyyymmdd, ddmmyyyy = date_formating(start_date_str)
        inst_list, market_df, exposure_df = get_inst_data(yyyymmdd)

        # 2) Paramètres de marché alignés à l’univers
        delta, market_weights = get_delta_and_weights(market_df)
        sigma = get_cov_matrix(market_df)
        pi = get_pi(delta, market_weights, sigma)

        # 3) Sérialisation JSON-safe pour dcc.Store
        market_payload = {
            "inst_list": list(inst_list),                     # si ids sont ints
            "delta": float(delta),
            "market_weights": np.asarray(market_weights).tolist(),
            "sigma": np.asarray(sigma).tolist(),                 
            "pi": np.asarray(pi).tolist(),
        }

        inst_list_store_payload = list(inst_list)
        exposure_payload = exposure_df.to_dict("records") 
        # 4) Tableau d’aperçu
        summary = f"{len(inst_list)} instruments retenus (à partir du {ddmmyyyy})"

        return inst_list_store_payload, market_payload, summary, exposure_payload

    except Exception as e:
        return [], {}, f"Erreur lors de la construction de l’univers/marché : {e}", {}


@app.callback(
    Output("theme-dd", "options"),
    Input("inst-list-store", "data"),
    prevent_initial_call=False,
)
def build_theme_options(inst_list):
    if not inst_list:
        return []
    ac = asset_class.copy()

    # filtre Asset ∈ inst_list
    try:
        mask = ac["Asset"].astype(int).isin(pd.Series(inst_list, dtype=int))
    except Exception:
        mask = ac["Asset"].astype(str).isin(pd.Series(inst_list, dtype=str))
    ac_f = ac.loc[mask]
    # on saute les 3 premières colonnes comme avant
    cols = [c for c in ac_f.columns[3:] if ac_f[c].notna().any()]

    return [{"label": c, "value": c} for c in cols]


@app.callback(
    Output("value1-dd", "options"),
    Output("value1-dd", "value"),
    Input("theme-dd", "value"),
    State("inst-list-store", "data"),
    prevent_initial_call=False,
)
def update_value1(theme, inst_list):
    opts = options_for_theme(theme, inst_list)
    return opts, None

# (B) Alimenter Élement 2 selon le thème et l’élément 1 (on évite de proposer 2 fois le même)
@app.callback(
    Output("value2-dd", "options"),
    Output("value2-dd", "value"),
    Input("theme-dd", "value"),
    Input("value1-dd", "value"),
    State("inst-list-store", "data"),
    prevent_initial_call=False,
)
def update_value2(theme, val1, inst_list):
    opts = options_for_theme(theme, inst_list)
    if val1:
        opts = [o for o in opts if o["value"] != str(val1)]
    return opts, None

# (C) Ajouter la vue -> met à jour uniquement le tableau
@app.callback(
    Output("views-table", "data"),
    Input("add-view-btn", "n_clicks"),
    State("views-table", "data"),
    State("theme-dd", "value"),
    State("value1-dd", "value"),
    State("value2-dd", "value"),
    State("pct-input", "value"),
    prevent_initial_call=True,
)
def add_view(n_clicks, table_data, theme, val1, val2, pct):
    table_data = table_data or []
    if not theme or not val1 or not val2 or pct is None:
        return table_data
    row = {
        "theme": str(theme),
        "value1": str(val1),
        "op": "≥",
        "value2": str(val2),
        "pourcentage": float(pct),
    }
    return table_data + [row]

# (D) Synchroniser le store (utilisé par l’optimisation) depuis le tableau
@app.callback(
    Output("views-store", "data"),
    Input("views-table", "data"),
)
def sync_views_store(table_data):
    return table_data or []

@app.callback(
    Output("optim-results", "data"),
    Output("optim-results", "columns"),
    Output("optim-msg", "children"),
    Input("run-optim-btn", "n_clicks"),
    State("views-store", "data"),
    State("fonds-dropdown", "value"),
    State("inst-list-store", "data"),
    State("market-store", "data"),
    State("tau-input", "value"),
    State("inst-exposure-store", "data"),  
    prevent_initial_call=True,
)
def run_optim(n_clicks, store, selected_fund_label, inst_list_state, market, tau, exposure_df):
    # 0) validations visibles
    if not n_clicks:
        return no_update, no_update, no_update

    if not store:
        return [], [], "Aucune vue saisie. Ajoutez au moins une vue."

    if not inst_list_state or len(inst_list_state) == 0:
        return [], [], "Univers d'instruments vide. Sélectionnez la date."

    if not market or not market.get("inst_list"):
        return [], [], "Modèle de marché indisponible. Re-sélectionnez la date."
    tau = 0.025 if (tau is None or tau < 0) else float(tau)/100

    try:
        # Univers + paramètres de marché depuis le cache
        delta = float(market["delta"])
        sigma = np.array(market["sigma"])
        pi    = np.array(market["pi"])

        # 1) Vues
        df_views = pd.DataFrame(store)
        if df_views.empty:
            return [], [], "Les vues sont vides."

        id_fund = fonds_dict.get(selected_fund_label, selected_fund_label)

        # 2) P & Q (P aligné sur inst_list)
        Q = get_Q(df_views)
        df_for_P = df_views.rename(columns={"theme":"Set", "value1":"Position", "op":"Sign", "value2":"Relative"})

        P = get_P(df_for_P, asset_class, inst_list_state)

        # 3) contrôles de dimensions
        N = len(inst_list_state)
        if sigma.shape != (N, N):
            return [], [], f"Dimension de sigma incohérente: {sigma.shape} vs N={N}"
        if P.ndim != 2:
            return [], [], f"P doit être 2D, reçu ndim={P.ndim}"
        if P.shape[1] != N:
            return [], [], f"Dimension de P incohérente: {P.shape} vs N={N}"
        if Q is None or (np.ndim(Q) == 0) or (len(np.atleast_1d(Q)) != P.shape[0]):
            return [], [], f"Q doit avoir la même longueur que le nombre de vues: len(Q)={len(np.atleast_1d(Q))} vs k={P.shape[0]}"

        # 4) Black–Litterman
        omega = get_omega(tau, P, sigma)
        mu_bl, sigma_bl = get_BL(tau, sigma, pi, P, Q, omega)

        # 5) Optimisation

        col_bsup = ["max_action","max_fx_hors_UE","max_HY","max_emergent","max_modified_duration",
                    "max_convertibles","max_cocos","max_oblig","max_FIA","max_OPC_monetaire",
                    "max_OPCI","max_solidaire","max_FCPR","max_private_asset"]
        expo_col_bsup = ["am_expo_stock_net","am_expo_risk_fx_out_eu_net","am_expo_high_yield_net",
                        "am_expo_market_emerging_net","am_modified_duration","am_expo_convertible_net",
                        "am_expo_cocos_net","am_expo_bond_market_net","is_fia","is_monetaire",
                        "is_opci","is_solidaire","is_fcpr","is_private_asset"]
        col_binf = ["min_action","min_modified_duration","min_oblig","min_ISR","min_solidaire",
                    "min_SFDR89","min_opc_pea_pme"]
        expo_col_binf = ["am_expo_stock_net","am_modified_duration","am_expo_bond_market_net",
                        "is_isr","is_solidaire","is_sfdr89","is_pea_pme"]
        
        exposure_df = pd.DataFrame(exposure_df)
        # Sanity check (détecte tout désalignement avant de construire A)
        try:
            assert list(pd.Index(exposure_df["id_inst"])) == list(inst_list_state)
        except AssertionError:
            return [], [], "Désalignement entre exposure_df et inst_list. Vérifie l'ordre des instruments."
        
        A, b = get_matrix_contraintes(inst_list_state, contraints_df, exposure_df, id_fund, col_bsup, col_binf, expo_col_bsup, expo_col_binf)
        contraintes, w, cash = get_cvxpy_contraintes(contraints_df, exposure_df, id_fund, A, b, inst_list_state)
        sigma_psd = psd_projection(sigma_bl)
        weights_df, cash = get_optimisation(inst_list_state, contraintes, w, cash, delta, mu_bl, sigma_psd)

        # 6) Formatage
        out_df = weights_df.copy()
        # On récupère aussi le code ISIN
        inst_info = load_sql("SELECT id_inst, code_isin, nm_inst FROM AssetDescription")
        inst_info = inst_info[inst_info["id_inst"].isin(out_df["id_inst"])]

        # Jointure pour ajouter le code_isin
        out_df = pd.merge(out_df, inst_info[["id_inst", "code_isin"]], on="id_inst", how="left")

        # Réorganiser les colonnes dans l’ordre voulu
        out_df = out_df[["id_inst", "code_isin", "nm_inst", "weight"]]

        # Ajouter le cash
        cash_row = pd.DataFrame([{"id_inst": None, "code_isin": None, "nm_inst": "CASH", "weight": cash}])
        out_df = pd.concat([out_df, cash_row], ignore_index=True)

        # Colonnes pour le DataTable
        columns = [{"name": c, "id": c} for c in out_df.columns]
        data = out_df.to_dict("records")

        return data, columns, "Optimisation terminée."

    except Exception as e:
        # Log serveur + retour UI
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        return [], [], f"Erreur pendant l’optimisation : {e}"
    

if __name__ == "__main__":
    app.run(debug=False, threaded=True, host='0.0.0.0', port=8051)