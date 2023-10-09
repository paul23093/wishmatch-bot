create table users_wishes (
    id int GENERATED ALWAYS AS identity,
    tg_user_id integer not null,
    name varchar(200) not null,
    description varchar(2000),
    price varchar(20),
    currency varchar(10),
    link varchar(3000),
    image varchar(3000),
    is_booked boolean default false,
    booked_by integer,
    is_deleted boolean default false,
    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp 
)
