CREATE TABLE IF NOT EXISTS core_notacalendario (
    id varchar(100) PRIMARY KEY NOT NULL,
    dados text NOT NULL CHECK (JSON_VALID(dados))
);
