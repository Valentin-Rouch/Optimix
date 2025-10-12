from data_access.sql_loader import load_sql
from librairies import *

def get_market_data(start_date_str):
    start_date = pd.to_datetime(start_date_str)
    date   = start_date + pd.Timedelta(days=7)
    date = date.date()
    date = date.strftime("%Y%m%d")
    sql_market = f"select v.id_inst, v.dt_calendar, v.am_capital_total_eur as am_capital, v.am_price from (select a.id_inst from AssetDescription a inner join ValuationSupply v on v.id_inst = a.id_inst and v.am_capital_total_eur is not null and v.dt_calendar >= '{start_date_str}' where a.nm_typ_asset in ('Fonds', 'Etf') and a.flg_closed = 0 and a.flg_synchronized = 1 group by a.id_inst having min(v.dt_calendar) <= '{date}') as i (id_inst) inner join ValuationSupply v on v.id_inst = i.id_inst and v.dt_calendar >= '{start_date_str}' left join (select id_inst from ValuationSupply where am_capital_total_eur is null and dt_calendar >= '{date}' group by id_inst) as n (id_inst) on n.id_inst = i.id_inst where n.id_inst is null"
    market_df = load_sql(sql_market)

    return market_df

def get_transparisation_data():
    sql_transparisation = f"select a.id_inst, a.am_expo_stock_net, a.am_expo_risk_fx_out_eu_net, a.am_expo_high_yield_net, a.am_expo_market_emerging_net, a.am_modified_duration, a.am_expo_bond_market_eu_net, a.am_expo_bond_market_out_eu_net, a.am_expo_convertible_net, a.am_expo_cocos_net from AssetExposure a inner join (select id_inst, max(dt_calendar) as dt_calendar from AssetExposure group by id_inst) as i (id_inst, dt_calendar) on i.id_inst = a.id_inst and i.dt_calendar = a.dt_calendar" 
    transparisation_df = load_sql(sql_transparisation)

    return transparisation_df

def get_inst_characteristics():
    sql_characteristics = f"select a.id_inst, iif(a.id_classification_sfdr = 68, 0, 1) as is_sfdr89, iif(a.id_issuer_parent in (18, 41, 49, 74, 89, 127, 171), 1, 0) as is_sdg_natixis, iif(a.id_category_global_fund in (1168, 1169, 1199), 1, 0) as is_monetaire, iif(a.flg_peapme = 'TRUE', 1, 0) as is_pea_pme, iif(a.flg_ucits = 'TRUE', 1, 0) as is_ucits, iif(a.id_typ_family_fund = 205, 1, 0) as is_fia, iif(a.id_typ_legal_structure = 215, 1, 0) as is_opci, iif(a.id_typ_legal_structure = 224, 1, 0) as is_fcpr, iif(a.id_category_global_fund in (1227, 1660), 1, 0) as is_private_asset, iif(i.nm_label_isr like '%Label Isr%', 1, 0) as is_isr, iif(i.nm_label_isr like '%Label Finansol%', 1, 0) as is_solidaire from AssetDescription a left join IsrAssetDescription i on i.id_inst = a.id_inst where a.nm_typ_asset in ('Fonds', 'Etf')"
    characteristics_df = load_sql(sql_characteristics)

    return characteristics_df

def get_inst_exposure():
    transparisation_df = get_transparisation_data()
    characteristics_df = get_inst_characteristics()
    exposure_df = pd.merge(transparisation_df, characteristics_df, on="id_inst", how="inner")
    exposure_df["am_expo_bond_market_net"] = exposure_df["am_expo_bond_market_eu_net"] + exposure_df["am_expo_bond_market_out_eu_net"]
    percent_cols = [
    "am_expo_stock_net",
    "am_expo_risk_fx_out_eu_net",
    "am_expo_high_yield_net",
    "am_expo_market_emerging_net",
    "am_expo_convertible_net",
    "am_expo_cocos_net",
    "am_expo_bond_market_net"]
    for c in percent_cols:
        if c in exposure_df.columns:
            exposure_df[c] = exposure_df[c] / 100.0

    return exposure_df

def get_inst_data(start_date_str):
    market_df = get_market_data(start_date_str)
    exposure_df = get_inst_exposure()
    mapping_inst_fund_df = load_sql(f"SELECT id_inst, id_inst_base FROM AssetDescription")

    # Intersections en conservant l'ordre d'apparition dans market_df
    inst_ordered = market_df["id_inst"].drop_duplicates()
    inst_expo_set = set(exposure_df["id_inst"])
    inst_list = [i for i in inst_ordered if i in inst_expo_set]

    # Retirer des ids spécifiques
    list_to_remove = [512, 748, 273, 653, 766, 833]
    inst_list = [i for i in inst_list if i not in list_to_remove]

    mapping_inst_fund_df = mapping_inst_fund_df[mapping_inst_fund_df["id_inst"].isin(inst_list)]
    df_unique = mapping_inst_fund_df.drop_duplicates(subset="id_inst_base", keep="first")
    inst_list = df_unique["id_inst"].tolist()

    # Filtrer et réordonner les DF selon inst_list
    market_df  = market_df[market_df["id_inst"].isin(inst_list)]
    exposure_df = (exposure_df
                .set_index("id_inst")
                .loc[inst_list]      # impose le même ordre que inst_list
                .reset_index())

    return inst_list, market_df, exposure_df