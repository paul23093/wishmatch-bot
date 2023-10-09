create table permissions (
  id integer GENERATED ALWAYS AS IDENTITY,
  tg_user_id integer not null,
  tg_chat_id float not null,
  is_deleted boolean not null default false,
  created_at timestamp default current_timestamp,
  updated_at timestamp default current_timestamp,
  CONSTRAINT pk_perm unique (tg_user_id, tg_chat_id)
)
