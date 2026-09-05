import pandas as pd
import hashlib


def drop_doi_queries(df):
    """
    Takes df as an input and returns df withouth doi queries
    """

    mask = df["query"].str.contains(r'10\.\d{4,}/', regex=True, na=False)
    return df[~mask]


def drop_undefined_track_ids(df):
    """
    Removes rows where 'trackId' starts with 'undefined'.
    If the column does not exist, the dataframe is returned unchanged.
    """
    if 'trackId' not in df.columns:
        return df  

    # Create a mask for rows starting with 'undefined'
    mask = df['trackId'].astype(str).str.startswith('undefined', na=False)

    # Return all rows that do NOT match
    return df[~mask]


def drop_track_ids(df):
    df = df.drop(columns=['type'], errors='ignore').dropna(thresh=2)
    return df

def dont_drop_track_ids(df):
    """
    Behält nur Zeilen, bei denen 'type' existiert
    und der Wert entweder 'author' oder 'works' ist.
    """
    if 'type' not in df.columns:
        return df.iloc[0:0]

    mask = (
        df['type'].notna() &
        df['type'].astype(str).isin({'author', 'works', 'get-pdf'})
    )

    return df[mask].copy()



def drop_title_queries(df):
    mask = df['query'].str.contains(r'title:"', regex=True, na=False)
    return df[~mask]

def hash_string(string):
    return hashlib.sha256(string.encode('utf-8')).hexdigest()


def limit_high_frequency_queries(df, limit):
    if 'query_hashed' not in df.columns:
       df['query_hashed'] = df['query'].apply(hash_string) 
    
    df['frequency'] = df.groupby('query_hashed').cumcount() + 1
    df.query(f'frequency <= {limit}', inplace = True)
    return df


def drop_high_frequency_queries(df, limit):
    if 'query_hashed' not in df.columns: 
        df['query_hashed'] = df['query'].apply(hash_string)

    df_grouped_by_query = df.groupby('query_hashed')['query'].count().sort_values(ascending=False)
    df_grouped_by_query = df_grouped_by_query.to_frame().reset_index().rename(columns = {"query" : "query_count"})
    df_grouped_by_query.query(f'query_count >= {limit}', inplace=True)
    df_merged = pd.merge(df, df_grouped_by_query, how='left', on='query_hashed', validate='m:1')
    df = df_merged[df_merged['query_count'].isnull()].drop(columns={'query_count', 'query_hashed'})

    return df



def drop_high_frequency_uids(df, limit=100):
    """
    Drops rows belonging to UIDs that appear more than `limit` times.
    If no 'uid' column exists, the dataframe is returned unchanged.
    """

    if 'uid' not in df.columns:
        # nothing to do → keep pipeline running
        return df

    rows_before = len(df)

    uid_counts = df['uid'].value_counts()
    high_freq_uids = uid_counts[uid_counts > limit].index

    df = df[~df['uid'].isin(high_freq_uids)].copy()

    rows_after = len(df)
    print(f"Deletes rows (uid): {rows_before - rows_after}")

    return df

def drop_nan_uids(df):
    """
    Entfernt alle Zeilen, bei denen 'uid' NaN ist.
    """
    if 'uid' not in df.columns:
        return df.iloc[0:0]
    rows_before = len(df)
    df = df[df['uid'].notna()].copy()
    rows_after = len(df)
    print(f"Delete rows (uid=NaN): {rows_before - rows_after}")
    return df

def drop_null_string_uids(df):
    """
    Entfernt alle Zeilen, bei denen 'uid' als String 'null' oder 'NaN' gespeichert ist.
    """
    if 'uid' not in df.columns:
        return df.iloc[0:0]
    rows_before = len(df)
    df = df[~df['uid'].isin(['null', 'NaN'])].copy()
    rows_after = len(df)
    print(f"Delete rows (uid='null'/'NaN'): {rows_before - rows_after}")
    return df

def keep_public_uids(df):
    """
    Keeps only rows where 'uid' starts with 'public'.
    Drops all other rows (including NaN/null/other strings).
    If the 'uid' column does not exist, returns an empty DataFrame.
    """
    if 'uid' not in df.columns:
        print("Spalte 'uid' existiert nicht → leeres DataFrame zurückgegeben")
        return df.iloc[0:0] 
    
    rows_before = len(df)
    
    # Keep only rows where uid is a string and starts with 'public'
    df = df[df['uid'].astype(str).str.startswith('public')].copy()
    
    rows_after = len(df)
    print(f"Entfernte Zeilen (uid nicht 'public*'): {rows_before - rows_after}")
    
    return df

def drop_boolean_queries(df):
    """
    Entfernt alle Zeilen, deren 'query' die Boolean-Operatoren
    AND, OR, NOT (case-sensitive) enthält.
    """
    if 'query' not in df.columns:
        return df
    
    mask = df['query'].str.contains(r'\b(AND|OR|NOT)\b', regex=True, na=False)
    removed = mask.sum()
    df = df[~mask].copy()
    print(f"Deletes rows (Boolean-Operators): {removed}")
    return df


def drop_special_field_queries(df):
    """
    Entfernt alle Zeilen, deren 'query' eines der speziellen Felder enthält:
    abstract, acceptedDate, arxivId, authors, citationCount, contributors, ...
    sowie _exists_ und andere im Pattern definierte Felder.
    """
    if 'query' not in df.columns:
        return df

    fields = [
        "abstract","acceptedDate","arxivId","authors","citationCount","contributors",
        "createdDate","dataProviders","depositedDate","documentType","doi","downloadUrl",
        "fieldOfStudy","fullText","identifiers","journals","links","magId","oaiIds",
        "outputs","publishedDate","publisher","pubmedId","references","sourceFulltextUrls",
        "title","updatedDate","yearPublished","language","_exists_","id","yearpublished","updateddate"
    ]

    # Build regex pattern: any field followed by a colon
    pattern = r'(^|[[:space:]]|[^a-zA-Z0-9])(' + '|'.join(fields) + r'):'

    mask = df['query'].str.contains(pattern, regex=True, na=False)
    removed = mask.sum()
    df = df[~mask].copy()
    print(f"Delete rows (special fields): {removed}")
    return df
