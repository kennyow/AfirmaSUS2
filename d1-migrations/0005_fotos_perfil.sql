CREATE TABLE IF NOT EXISTS cloudpilot_fotoperfil (
    usuario_id integer PRIMARY KEY REFERENCES auth_user(id),
    arquivo varchar(200) NOT NULL
);
