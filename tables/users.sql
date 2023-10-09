create table users (
	id int GENERATED ALWAYS AS identity,
	tg_user_id integer not null,
	tg_username varchar(50),
	tg_first_name varchar(50),
	tg_last_name varchar(50),
	tg_profile_photo varchar(50000),
	created_at timestamp default current_timestamp,
	updated_at timestamp default current_timestamp,
	constraint pk_user unique(tg_user_id)
);
