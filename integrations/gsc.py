import os, datetime
import db

def _get_service(tenant_id, projeto_id):
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    token_row = db.query_one(
        "SELECT * FROM oauth_tokens WHERE tenant_id=%s AND projeto_id=%s AND provedor='google'",
        (tenant_id, projeto_id)
    )
    if not token_row:
        raise ValueError("Token Google não configurado.")
    creds = Credentials(
        token=token_row["access_token"],
        refresh_token=token_row["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )
    return build("searchconsole", "v1", credentials=creds)

def coletar_queries(tenant_id, projeto_id, site_url, dias=28):
    try:
        service    = _get_service(tenant_id, projeto_id)
        end_date   = datetime.date.today() - datetime.timedelta(days=3)
        start_date = end_date - datetime.timedelta(days=dias)
        body = {
            "startDate": str(start_date), "endDate": str(end_date),
            "dimensions": ["query","page","date"], "rowLimit": 1000,
        }
        rows = service.searchanalytics().query(siteUrl=site_url, body=body).execute().get("rows",[])
        for row in rows:
            keys = row.get("keys",[])
            db.execute("""
                INSERT INTO gsc_metricas
                    (tenant_id, projeto_id, data_ref, query, pagina,
                     cliques, impressoes, ctr, posicao_media)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
            """, (
                tenant_id, projeto_id,
                keys[2] if len(keys)>2 else None,
                keys[0] if len(keys)>0 else None,
                keys[1] if len(keys)>1 else None,
                row.get("clicks",0), row.get("impressions",0),
                round(row.get("ctr",0),4), round(row.get("position",0),2),
            ))
        return {"status":"ok","linhas":len(rows)}
    except Exception as e:
        return {"status":"erro","detalhe":str(e)}

def resumo_gsc(tenant_id, projeto_id, dias=28):
    end_date   = datetime.date.today() - datetime.timedelta(days=3)
    start_date = end_date - datetime.timedelta(days=dias)
    row = db.query_one("""
        SELECT SUM(cliques) AS total_cliques, SUM(impressoes) AS total_impressoes,
               AVG(ctr) AS ctr_medio, AVG(posicao_media) AS posicao_media
        FROM gsc_metricas
        WHERE tenant_id=%s AND projeto_id=%s AND data_ref BETWEEN %s AND %s
    """, (tenant_id, projeto_id, start_date, end_date))
    return dict(row) if row else {}

def top_queries(tenant_id, projeto_id, limite=10, dias=28):
    end_date   = datetime.date.today() - datetime.timedelta(days=3)
    start_date = end_date - datetime.timedelta(days=dias)
    return db.query("""
        SELECT query, SUM(cliques) AS cliques, SUM(impressoes) AS impressoes,
               AVG(posicao_media)::numeric(5,1) AS posicao
        FROM gsc_metricas
        WHERE tenant_id=%s AND projeto_id=%s AND data_ref BETWEEN %s AND %s
          AND query IS NOT NULL
        GROUP BY query ORDER BY cliques DESC LIMIT %s
    """, (tenant_id, projeto_id, start_date, end_date, limite))

def tendencia_cliques(tenant_id, projeto_id, dias=28):
    end_date   = datetime.date.today() - datetime.timedelta(days=3)
    start_date = end_date - datetime.timedelta(days=dias)
    return db.query("""
        SELECT data_ref, SUM(cliques) AS cliques, SUM(impressoes) AS impressoes
        FROM gsc_metricas
        WHERE tenant_id=%s AND projeto_id=%s AND data_ref BETWEEN %s AND %s
        GROUP BY data_ref ORDER BY data_ref
    """, (tenant_id, projeto_id, start_date, end_date))
