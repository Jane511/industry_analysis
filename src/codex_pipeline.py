from __future__ import annotations
from pathlib import Path
import pandas as pd
from .codex_config import PROJECT_ROOT, REPO_NAME, PIPELINE_KIND, EXPECTED_OUTPUTS

DEMO = [
{'borrower_id':'B001','facility_id':'F001','segment':'SME Cash Flow','industry':'Wholesale Trade','product_type':'term_loan','limit':1200000,'drawn':980000,'current_assets':1650000,'current_liabilities':920000,'inventory':410000,'receivables':560000,'payables':390000,'revenue':5200000,'ebitda':620000,'net_debt':1450000,'debt_service':360000,'collateral':1500000,'haircut':.18,'pd':.018,'lgd':.42,'ead':1040000,'maturity':3},
{'borrower_id':'B002','facility_id':'F002','segment':'SME Cash Flow','industry':'Construction','product_type':'overdraft','limit':800000,'drawn':690000,'current_assets':980000,'current_liabilities':760000,'inventory':120000,'receivables':430000,'payables':520000,'revenue':3700000,'ebitda':310000,'net_debt':1020000,'debt_service':295000,'collateral':620000,'haircut':.25,'pd':.052,'lgd':.58,'ead':742000,'maturity':1},
{'borrower_id':'B003','facility_id':'F003','segment':'Property Backed','industry':'Accommodation and Food Services','product_type':'commercial_mortgage','limit':2400000,'drawn':2100000,'current_assets':1450000,'current_liabilities':840000,'inventory':70000,'receivables':290000,'payables':310000,'revenue':6100000,'ebitda':760000,'net_debt':2600000,'debt_service':540000,'collateral':3300000,'haircut':.22,'pd':.034,'lgd':.33,'ead':2220000,'maturity':4},
{'borrower_id':'B004','facility_id':'F004','segment':'Working Capital','industry':'Manufacturing','product_type':'revolving_working_capital','limit':1500000,'drawn':830000,'current_assets':2200000,'current_liabilities':1340000,'inventory':760000,'receivables':690000,'payables':610000,'revenue':7300000,'ebitda':880000,'net_debt':1750000,'debt_service':470000,'collateral':1180000,'haircut':.20,'pd':.026,'lgd':.47,'ead':1100000,'maturity':2.5},
{'borrower_id':'B005','facility_id':'F005','segment':'Trade Finance','industry':'Retail Trade','product_type':'trade_finance','limit':600000,'drawn':210000,'current_assets':1120000,'current_liabilities':690000,'inventory':540000,'receivables':250000,'payables':430000,'revenue':4500000,'ebitda':390000,'net_debt':720000,'debt_service':230000,'collateral':480000,'haircut':.28,'pd':.041,'lgd':.55,'ead':420000,'maturity':1.5},
{'borrower_id':'B006','facility_id':'F006','segment':'Contingent','industry':'Professional Services','product_type':'guarantee','limit':950000,'drawn':0,'current_assets':1850000,'current_liabilities':740000,'inventory':30000,'receivables':620000,'payables':280000,'revenue':6800000,'ebitda':1040000,'net_debt':430000,'debt_service':210000,'collateral':900000,'haircut':.16,'pd':.012,'lgd':.36,'ead':285000,'maturity':2},
]

def _div(a,b):
    return (a / b.replace(0, pd.NA)).fillna(0)

def load_demo(path: Path | None = None) -> pd.DataFrame:
    path = path or PROJECT_ROOT / 'data' / 'raw' / 'demo_portfolio.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists(): pd.DataFrame(DEMO).to_csv(path, index=False)
    return pd.read_csv(path)

def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    d=raw.copy(); d['undrawn']=d['limit']-d['drawn']; d['utilisation']=_div(d['drawn'],d['limit']).clip(0,1.5)
    d['margin']=_div(d['ebitda'],d['revenue']); d['dscr']=_div(d['ebitda'],d['debt_service']); d['leverage']=_div(d['net_debt'],d['ebitda'])
    d['working_capital_ratio']=_div(d['current_assets'],d['current_liabilities']); d['quick_ratio']=_div(d['current_assets']-d['inventory'],d['current_liabilities']); d['collateral_coverage']=_div(d['collateral'],d['ead'])
    d['receivables_days']=(_div(d['receivables'],d['revenue'])*365).round(1); d['inventory_days']=(_div(d['inventory'],d['revenue']*.65)*365).round(1); d['payables_days']=(_div(d['payables'],d['revenue']*.7)*365).round(1); d['cash_conversion_cycle']=d['receivables_days']+d['inventory_days']-d['payables_days']
    return d

def _grade(x):
    return 'RG1' if x<=.01 else 'RG2' if x<=.025 else 'RG3' if x<=.05 else 'RG4' if x<=.09 else 'RG5'

def _decision(r):
    return 'Decline' if r.pd_estimate>=.085 or r.dscr<1 else 'Refer' if r.pd_estimate>=.04 or r.dscr<1.25 else 'Approve'

def build_outputs(f: pd.DataFrame) -> dict[str,pd.DataFrame]:
    if PIPELINE_KIND=='financial':
        flags=f[['borrower_id','facility_id','segment','industry','dscr','leverage','quick_ratio']].copy(); flags['qualitative_risk_flag']=flags.apply(lambda r:'; '.join([n for n,c in {'low_dscr':r.dscr<1.25,'high_leverage':r.leverage>3.5,'weak_liquidity':r.quick_ratio<1}.items() if c]) or 'no_major_flag',axis=1)
        diag=f.groupby(['segment','industry'],as_index=False).agg(avg_dscr=('dscr','mean'),avg_margin=('margin','mean'),avg_leverage=('leverage','mean'),facilities=('facility_id','count')); diag['trend_risk']=diag.avg_dscr.apply(lambda v:'elevated' if v<1.25 else 'stable')
        return {'standardised_borrower_financials.csv':f[['borrower_id','facility_id','segment','industry','revenue','ebitda','margin','net_debt','debt_service','dscr']], 'ratio_summary_tables.csv':f[['borrower_id','facility_id','leverage','working_capital_ratio','quick_ratio','collateral_coverage','utilisation']], 'working_capital_metrics.csv':f[['borrower_id','facility_id','receivables_days','inventory_days','payables_days','cash_conversion_cycle']], 'trend_diagnostics.csv':diag, 'qualitative_risk_flags.csv':flags}
    if PIPELINE_KIND=='industry':
        g=f.groupby('industry',as_index=False).agg(avg_dscr=('dscr','mean'),avg_margin=('margin','mean'),avg_utilisation=('utilisation','mean'),exposure=('ead','sum'),facilities=('facility_id','count')); g['industry_risk_score']=(5-g.avg_dscr.clip(0,2.5)+g.avg_utilisation*2-g.avg_margin.clip(0,.3)).clip(1,5)
        down=g[['industry','industry_risk_score']].copy(); down['pd_overlay_multiplier']=1+down.industry_risk_score*.08; down['lgd_overlay_addon']=down.industry_risk_score*.015
        soft=g[['industry','avg_utilisation','avg_margin']].copy(); soft['market_softness_band']=soft.apply(lambda r:'soft' if r.avg_utilisation>.75 or r.avg_margin<.09 else 'normal',axis=1)
        conc=g[['industry','exposure','facilities']].copy(); conc['portfolio_share']=conc.exposure/conc.exposure.sum(); conc['concentration_flag']=conc.portfolio_share.apply(lambda v:'review' if v>.30 else 'within_demo_limit')
        return {'industry_risk_score_table.csv':g,'benchmark_ratio_reference_table.csv':g[['industry','avg_dscr','avg_margin','avg_utilisation','facilities']],'downturn_overlay_table.csv':down,'market_softness_overlay.csv':soft,'concentration_support_table.csv':conc}
    if PIPELINE_KIND=='pd':
        w=f.copy(); w['pd_estimate']=(w.pd*(1+(1.25-w.dscr).clip(lower=0)*.20+w.utilisation.clip(0,1)*.10)).clip(.002,.35); w['score']=(720-w.pd_estimate*2500+w.dscr.clip(0,3)*18+w.margin.clip(0,.4)*100-w.leverage.clip(0,8)*9).round(0); w['risk_grade']=w.pd_estimate.apply(_grade)
        out=w[['borrower_id','facility_id','segment','industry','product_type','score','risk_grade','pd_estimate','dscr','utilisation']].copy(); out['policy_decision']=w.apply(_decision,axis=1)
        return {'pd_model_output.csv':out.drop(columns=['policy_decision']),'borrower_grade_summary.csv':w.groupby('risk_grade',as_index=False).agg(borrowers=('borrower_id','nunique'),facilities=('facility_id','count'),exposure=('ead','sum'),avg_pd=('pd_estimate','mean')),'policy_decisions.csv':out,'score_band_output.csv':w.groupby('risk_grade',as_index=False).agg(min_score=('score','min'),max_score=('score','max'),min_pd=('pd_estimate','min'),max_pd=('pd_estimate','max'),facilities=('facility_id','count'))}
    if PIPELINE_KIND=='lgd':
        w=f.copy(); w['net_collateral']=w.collateral*(1-w.haircut); w['workout_cost']=w.ead*.06; w['net_recovery']=(w.net_collateral-w.workout_cost).clip(lower=0); w['lgd_final']=(1-w.net_recovery/w.ead.replace(0,pd.NA)).fillna(1).clip(.10,.90); w['downturn_lgd']=(w.lgd_final+.08+w.haircut*.10).clip(upper=.95)
        val=pd.DataFrame([{'check_name':'lgd_between_zero_and_one','status':w.lgd_final.between(0,1).all()},{'check_name':'downturn_not_below_base','status':(w.downturn_lgd>=w.lgd_final).all()}])
        return {'lgd_segment_summary.csv':w.groupby(['segment','product_type'],as_index=False).agg(facilities=('facility_id','count'),exposure=('ead','sum'),avg_lgd=('lgd_final','mean'),avg_downturn_lgd=('downturn_lgd','mean')),'recovery_waterfall.csv':w[['facility_id','borrower_id','product_type','ead','collateral','haircut','net_collateral','workout_cost','net_recovery','lgd_final']],'downturn_lgd_output.csv':w[['facility_id','borrower_id','segment','lgd_final','downturn_lgd']],'lgd_validation_report.csv':val}
    if PIPELINE_KIND=='ead':
        w=f.copy(); mp={'term_loan':0,'overdraft':.65,'commercial_mortgage':.20,'revolving_working_capital':.55,'trade_finance':.45,'guarantee':.30}; w['base_ccf']=w.product_type.map(mp).fillna(.4); w['utilisation_uplift']=w.utilisation.apply(lambda v:.10 if v>.85 else .05 if v>.65 else .02); w['downturn_ccf']=(w.base_ccf+w.utilisation_uplift).clip(upper=1); w['ead_central']=w.drawn+w.undrawn*w.base_ccf; w['ead_downturn']=w.drawn+w.undrawn*w.downturn_ccf
        val=pd.DataFrame([{'check_name':'ccf_between_zero_and_one','status':w.downturn_ccf.between(0,1).all()},{'check_name':'ead_not_below_drawn','status':(w.ead_central>=w.drawn).all()},{'check_name':'ead_within_limit','status':(w.ead_central<=w.limit).all()}])
        return {'ead_by_facility.csv':w[['facility_id','borrower_id','product_type','limit','drawn','undrawn','utilisation','base_ccf','downturn_ccf','ead_central','ead_downturn']],'ccf_by_product.csv':w.groupby('product_type',as_index=False).agg(facilities=('facility_id','count'),avg_utilisation=('utilisation','mean'),avg_base_ccf=('base_ccf','mean'),avg_downturn_ccf=('downturn_ccf','mean')),'utilisation_uplift_tables.csv':w[['product_type','utilisation','base_ccf','utilisation_uplift','downturn_ccf']],'ead_validation_report.csv':val}
    if PIPELINE_KIND=='el':
        w=f.copy(); w['expected_loss_12m']=w.pd*w.lgd*w.ead; w['lifetime_pd']=(w.pd*w.maturity*1.15).clip(upper=.75); w['expected_loss_lifetime']=w.lifetime_pd*w.lgd*w.ead
        scen=pd.DataFrame([{'scenario':'base','weight':.60,'pd_multiplier':1,'lgd_multiplier':1},{'scenario':'mild_downturn','weight':.25,'pd_multiplier':1.3,'lgd_multiplier':1.08},{'scenario':'severe_downturn','weight':.15,'pd_multiplier':1.7,'lgd_multiplier':1.18}]); scen['scenario_expected_loss']=scen.apply(lambda r:(w.pd*r.pd_multiplier*w.lgd*r.lgd_multiplier*w.ead).sum(),axis=1); scen['weighted_expected_loss']=scen.scenario_expected_loss*scen.weight
        return {'expected_loss_by_facility.csv':w[['facility_id','borrower_id','segment','product_type','pd','lgd','ead','expected_loss_12m','lifetime_pd','expected_loss_lifetime']],'expected_loss_by_borrower.csv':w.groupby('borrower_id',as_index=False).agg(facilities=('facility_id','count'),total_ead=('ead','sum'),expected_loss_12m=('expected_loss_12m','sum'),expected_loss_lifetime=('expected_loss_lifetime','sum')),'expected_loss_by_segment.csv':w.groupby('segment',as_index=False).agg(facilities=('facility_id','count'),total_ead=('ead','sum'),expected_loss_12m=('expected_loss_12m','sum'),expected_loss_lifetime=('expected_loss_lifetime','sum')),'portfolio_expected_loss.csv':pd.DataFrame([{'portfolio':'demo_portfolio','facilities':len(w),'total_ead':w.ead.sum(),'expected_loss_12m':w.expected_loss_12m.sum(),'expected_loss_lifetime':w.expected_loss_lifetime.sum()}]),'scenario_weighted_ecl.csv':scen}
    w=f.copy(); w['risk_weight']=(.45+w.pd*8+w.lgd*.50+w.maturity*.03).clip(.35,1.50); w['rwa']=w.ead*w.risk_weight; w['capital_requirement']=w.rwa*.105; w['expected_loss']=w.pd*w.lgd*w.ead; w['capital_after_el_adjustment']=(w.capital_requirement-w.expected_loss).clip(lower=0)
    return {'rwa_by_facility.csv':w[['facility_id','borrower_id','segment','product_type','pd','lgd','ead','maturity','risk_weight','rwa','capital_requirement']],'rwa_by_segment.csv':w.groupby('segment',as_index=False).agg(facilities=('facility_id','count'),total_ead=('ead','sum'),total_rwa=('rwa','sum'),capital_requirement=('capital_requirement','sum'),expected_loss=('expected_loss','sum')),'capital_summary.csv':pd.DataFrame([{'portfolio':'demo_portfolio','total_ead':w.ead.sum(),'total_rwa':w.rwa.sum(),'capital_requirement':w.capital_requirement.sum(),'capital_ratio_assumption':.105}]),'expected_loss_adjustment_summary.csv':w[['facility_id','expected_loss','capital_requirement','capital_after_el_adjustment']]}

def validate_outputs(o: dict[str,pd.DataFrame]) -> pd.DataFrame:
    rows=[{'check_name':f'required_output::{n}','status':n in o and not o[n].empty,'detail':'present and non-empty' if n in o and not o[n].empty else 'missing or empty'} for n in EXPECTED_OUTPUTS]
    for name,df in o.items():
        nums=df.select_dtypes('number')
        for col in nums.columns:
            c=col.lower()
            if any(t in c for t in ['pd','lgd','ccf','utilisation','risk_weight','margin','ratio','ead','exposure','capital','loss','rwa','recovery','collateral']): rows.append({'check_name':f'non_negative::{name}::{col}','status':bool((nums[col]>=0).all()),'detail':'all values non-negative'})
    return pd.DataFrame(rows)

def write_outputs(o: dict[str,pd.DataFrame], root: Path) -> dict[str,Path]:
    out=root/'outputs'/'tables'; out.mkdir(parents=True,exist_ok=True); paths={}
    for n,df in o.items():
        p=out/n; df.round(4).to_csv(p,index=False); paths[n]=p
    return paths

def run_pipeline(project_root: Path | str | None=None, persist: bool=True) -> dict[str,object]:
    root=Path(project_root) if project_root else PROJECT_ROOT; raw=load_demo(root/'data'/'raw'/'demo_portfolio.csv'); feat=build_features(raw); outs=build_outputs(feat); val=validate_outputs(outs); outs['pipeline_validation_report.csv']=val
    paths={}
    if persist:
        (root/'data'/'processed').mkdir(parents=True,exist_ok=True); (root/'outputs'/'samples').mkdir(parents=True,exist_ok=True); (root/'outputs'/'reports').mkdir(parents=True,exist_ok=True)
        feat.to_csv(root/'data'/'processed'/'feature_table.csv',index=False); raw.to_csv(root/'outputs'/'samples'/'demo_input.csv',index=False); paths=write_outputs(outs,root)
        (root/'outputs'/'reports'/'pipeline_summary.md').write_text(f'# Pipeline Summary - {REPO_NAME}\n\nWrote {len(paths)} output tables. Validation checks passed: {int(val.status.sum())}/{len(val)}.\n',encoding='utf-8')
    return {'raw':raw,'features':feat,'outputs':outs,'validation':val,'output_paths':paths}

def main() -> None:
    r=run_pipeline(); print(f"{REPO_NAME}: wrote {len(r['outputs'])} output tables")
