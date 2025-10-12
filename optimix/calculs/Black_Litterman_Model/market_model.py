from librairies import *
from data_access.sql_loader import load_sql

def pivot_capital(market_df):
    # 1) Nettoyage de base
    market_df["dt_calendar"] = pd.to_datetime(market_df["dt_calendar"])
    market_df = market_df.sort_values(["dt_calendar", "id_inst"])   
    # 2) Gérer d'éventuels doublons (même jour/même id_inst)
    # on prend la dernière valeur du jour
    g = (market_df.groupby(["dt_calendar", "id_inst"], as_index=False)["am_capital"].last())  
    # 3) Pivot large: index = date, colonnes = id_inst, valeurs = am_capital
    capital_df = g.pivot(index="dt_calendar", columns="id_inst", values="am_capital")     
    # 4) Renommer les colonnes: am_capital_<id>
    capital_df.columns = [f"am_capital_{int(c)}" for c in capital_df.columns]    
    # 5) Total quotidien et rendement
    capital_df = capital_df.sort_index()
    capital_df = capital_df.dropna()
    capital_df["am_capital_tot"] = capital_df.sum(axis=1, min_count=1)
    capital_df["return_tot"] = capital_df["am_capital_tot"].pct_change()
    return capital_df

def pivot_returns(market_df):
    market_df["dt_calendar"] = pd.to_datetime(market_df["dt_calendar"])  
    # 1) On garde une seule observation par (date, instrument)
    # (si doublons: on prend la dernière) (possibilité de changer en .first())
    g = (market_df.sort_values(["id_inst", "dt_calendar"]).groupby(["dt_calendar", "id_inst"], as_index=False)["am_price"].last())     
    # 2) Pivot large: colonnes = id_inst, index = date, valeurs = prix
    prices = (g.pivot(index="dt_calendar", columns="id_inst", values="am_price").sort_index())    
    # 3) Rendements simples: (P_t / P_{t-1}) - 1
    returns_df = prices.pct_change() 
    # 4) Renommer les colonnes: return_<id>
    returns_df.columns = [f"return_{int(c)}" for c in returns_df.columns]  
    # 5) Remplacer le premier NaN de chaque série par 0.0
    returns_df = returns_df.fillna(0.0) 
    # 6) Remplacer les inf (si prix précédent = 0) par 0.0
    returns_df = returns_df.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return returns_df

def get_delta_and_weights(market_df):
    capital_df = pivot_capital(market_df)
    # Calcul du taux sans risque
    start_date = capital_df.index[0]
    end_date = capital_df.index[-1]
    delta = end_date - start_date
    nb_jours = delta.days
    nb_annee = nb_jours/252
    
    str_price = load_sql(f"SELECT dt_calendar, am_price FROM ValuationDescription WHERE nm_inst =  '€STR CAPITALISÉ' AND flg_official = 1 ORDER BY dt_calendar")
    str_price = str_price[(str_price['dt_calendar'] >= start_date) & (str_price['dt_calendar'] <= end_date)]
    str_price['return'] = str_price['am_price'].pct_change()    
    risk_free = (1 + str_price['return']).prod() - 1
    risk_free_annualise = (risk_free + 1)**(1/nb_annee) - 1
    
    # Calcul du coefficient d'aversion au risque
    rendement_composé = (1 + capital_df['return_tot']).prod() - 1
    rendement_annualise = (rendement_composé + 1)**(1/nb_annee) - 1
    std = capital_df['return_tot'].std()
    sharpe = (rendement_annualise - risk_free_annualise)/std
    delta = sharpe/std
    
    # Calcul du dernier poids pour chaque instrument
    last_capital_tot = capital_df["am_capital_tot"].iloc[-1]
    last_row = capital_df.iloc[-1]
    last_capitals = last_row.filter(like="am_capital_")
    last_capitals = last_capitals.drop("am_capital_tot", errors="ignore")
    weights = last_capitals / last_capital_tot

    return delta, weights

def get_cov_matrix(market_df):
    returns_df = pivot_returns(market_df)
    cov_matrix = returns_df.cov()

    return cov_matrix

def get_pi(delta, market_weights, sigma):
    # Nettoyer les noms d'index de omega pour correspondre aux colonnes de sigma
    market_weights.index = [col.replace("am_capital_", "") for col in market_weights.index]
    # Même chose pour les colonnes/lignes de sigma si nécessaire
    sigma.columns = sigma.columns.astype(str)
    sigma.index = sigma.index.astype(str)
    w = market_weights.values.reshape(-1, 1)
    pi = pd.DataFrame(delta * sigma.values @ w, index=sigma.index, columns=["pi"])

    return pi

def psd_projection(sigma):
    sigma = sigma.astype(np.float64, copy=False)
    if not np.isfinite(sigma).all():
        raise ValueError("Sigma contient des NaN/Inf.")
    sigma = 0.5 * (sigma + sigma.T)
    vals, vecs = np.linalg.eigh(sigma)
    eps = 1e-12
    vals_clipped = np.clip(vals, 0.0, None) + eps
    sigma_psd = (vecs * vals_clipped) @ vecs.T
    sigma_psd = 0.5 * (sigma_psd + sigma_psd.T)

    return sigma_psd
