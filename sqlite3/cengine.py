from datetime import datetime, timedelta

def get_ptd(ctd_str: str) -> str:

    date_format = "%Y%m%d"
    ctd_date = datetime.strptime(ctd_str, date_format)
    
    if ctd_date.weekday() == 0:
        ptd_date = ctd_date - timedelta(days=3)
    elif ctd_date.weekday() == 6: # Sunday
        ptd_date = ctd_date - timedelta(days=2)
    else:
        ptd_date = ctd_date - timedelta(days=1)
        
    return ptd_date.strftime(date_format)