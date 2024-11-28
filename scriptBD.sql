create database emprego;

use emprego;

create table empresa (
    id_empresa INT PRIMARY KEY AUTO_INCREMENT,
    nome_empresa varchar(100) not null,
    cnpj char(14) not null,
    telefone char(11) not null,
    email varchar(100) unique not null,
    senha varchar(30) not null,
    status ENUM('ativa','inativa') default 'ativa' not null
);

create table vaga (
    id_vaga INT PRIMARY KEY AUTO_INCREMENT,
    titulo varchar(100) not null,
    descricao text not null,
    formato ENUM('Presencial','Híbrido','Remoto') not null,
    tipo ENUM('CLT','PJ') not null,
    local varchar(100),
    salario varchar(10),
    id_empresa int not null,
    status ENUM('ativa','inativa') default 'ativa' not null,
    foreign key (id_empresa) references empresa (id_empresa)
);

create table candidato (
    id_candidato INT PRIMARY KEY AUTO_INCREMENT,
    nome varchar(100) not null,
    email varchar(100) unique not null,
    telefone char(11) not null,
    curriculo varchar(50) not null,
    id_vaga int not null,
    foreign key (id_vaga) references vaga (id_vaga)
);

CREATE TABLE arquivo (
    id_arquivo INT PRIMARY KEY AUTO_INCREMENT,
    nome_arquivo VARCHAR(100) NOT NULL,
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);