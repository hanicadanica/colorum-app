create table colorum_admins(
  id varchar(30) not null,
  password text not null,
  primary key (id)
);

create table colorum_users(
  id varchar(30) not null,
  password text not null,
  primary key (id)
);

create table puv_routes(
  id varchar(30) not null,
  gpx_filename text,
  primary key (id)
);

create table gps_devices(
  id varchar(15) not null,
  online boolean default false,
  last_location float[2],
  associated_route varchar(30),
  primary key (id)
);