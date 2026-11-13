CREATE TABLE IF NOT EXISTS core_formacaopublicada (
    id integer PRIMARY KEY AUTOINCREMENT,
    titulo varchar(200) NOT NULL,
    descricao text NOT NULL,
    foto varchar(500) NOT NULL
);
