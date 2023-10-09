create table chats (
	id int GENERATED ALWAYS AS identity,
	tg_chat_id float not null,
	tg_chat_name varchar(50),
	tg_chat_photo varchar(50000),
	created_at timestamp default current_timestamp,
	updated_at timestamp default current_timestamp,
	constraint pk_chat unique(tg_chat_id)
);
