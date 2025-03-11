# Database Tables and Fields

## api_keys
- id (integer, NOT NULL, default: nextval('api_keys_id_seq'::regclass))
- api_key (uuid, default: uuid_generate_v4())
- location_id (integer, NOT NULL)
- name (character varying(255), NOT NULL)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)

## categories
- id (integer, NOT NULL, default: nextval('categories_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- name (text)
- description (text)
- menu_id (integer, NOT NULL)
- disabled (boolean)
- start_time (smallint)
- end_time (smallint)
- seq_num (integer, default: 0)

## device_sessions
- id (integer, NOT NULL, default: nextval('device_sessions_id_seq'::regclass))
- device_token (text)
- device_type (integer, NOT NULL)
- user_id (integer, NOT NULL)
- expires_at (timestamp with time zone)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)

## discounts
- id (integer, NOT NULL, default: nextval('discounts_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- order_id (integer, NOT NULL)
- user_id (integer, NOT NULL)
- amount (numeric, NOT NULL)
- reason (text)

## identities
- id (integer, NOT NULL, default: nextval('identities_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- provider (text)
- uid (text)
- user_id (integer, NOT NULL)
- picture (text)

## indicators
- id (integer, NOT NULL, default: nextval('indicators_id_seq'::regclass))
- name (character varying(255), NOT NULL)
- uid (character varying(255))
- location_id (integer, NOT NULL)
- api_key_id (integer, NOT NULL)
- status (integer, NOT NULL)
- last_contact (timestamp with time zone)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- version (character varying(10))

## items
- id (integer, NOT NULL, default: nextval('items_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- name (text)
- description (text)
- price (numeric, NOT NULL)
- category_id (integer, NOT NULL)
- disabled (boolean)
- seq_num (integer, default: 0)

## location_hours
- id (integer, NOT NULL, default: nextval('location_hours_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- location_id (integer, NOT NULL)
- day_of_week (character varying(10))
- time_slot (integer)
- open_time (time without time zone)
- close_time (time without time zone)

## locations
- id (integer, NOT NULL, default: nextval('locations_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- name (text)
- description (text)
- timezone (text, NOT NULL)
- latitude (double precision)
- longitude (double precision)
- active (boolean, NOT NULL, default: TRUE)
- disabled (boolean, NOT NULL, default: FALSE)
- code (text)
- tax_rate (numeric, default: 0)
- settings (json)

## markers
- id (integer, NOT NULL, default: nextval('markers_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- name (text)
- disabled (boolean, default: FALSE)
- location_id (integer, NOT NULL)

## menus
- id (integer, NOT NULL, default: nextval('menus_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- name (text)
- description (text)
- location_id (integer, NOT NULL)
- disabled (boolean)

## messages
- id (integer, NOT NULL, default: nextval('messages_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- content (text)
- sender_id (integer, NOT NULL)
- recipient_id (integer, NOT NULL)
- order_id (integer, NOT NULL)
- read (boolean, default: FALSE)

## new_option_id
- ?column? (integer)

## old_item_id
- id (integer)

## option_items
- id (integer, NOT NULL, default: nextval('option_items_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- name (text)
- description (text)
- price (numeric, NOT NULL)
- option_id (integer, NOT NULL)
- disabled (boolean)

## option_items_count
- count (bigint)

## options
- id (integer, NOT NULL, default: nextval('options_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- name (text)
- description (text)
- min (integer, NOT NULL)
- max (integer, NOT NULL)
- item_id (integer, NOT NULL)
- disabled (boolean)

## order_items
- id (integer, NOT NULL, default: nextval('order_items_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- item_id (integer, NOT NULL)
- quantity (integer, NOT NULL)
- order_id (integer, NOT NULL)
- instructions (text)

## order_option_items
- id (integer, NOT NULL, default: nextval('order_option_items_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- order_item_id (integer, NOT NULL)
- order_id (integer, NOT NULL)
- option_item_id (integer, NOT NULL)

## order_ratings
- id (integer, NOT NULL, default: nextval('order_ratings_id_seq'::regclass))
- order_id (integer, NOT NULL)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- acknowledged (boolean, default: FALSE)

## order_ratings_feedback
- id (integer, NOT NULL, default: nextval('order_ratings_feedback_id_seq'::regclass))
- value (integer, NOT NULL)
- notes (character varying(255))
- rating_id (integer, NOT NULL)
- category_id (integer, NOT NULL)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)

## order_ratings_feedback_responses
- id (integer, NOT NULL, default: nextval('order_ratings_feedback_responses_id_seq'::regclass))
- feedback_id (integer, NOT NULL)
- response_id (integer, NOT NULL)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)

## orders
- id (integer, NOT NULL, default: nextval('orders_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- customer_id (integer, NOT NULL)
- vendor_id (integer, NOT NULL)
- location_id (integer, NOT NULL)
- status (integer, NOT NULL)
- total (numeric, NOT NULL)
- tax (numeric, NOT NULL)
- instructions (text)
- type (integer, NOT NULL)
- marker_id (integer, NOT NULL)
- fee (numeric, default: 0)
- loyalty_id (character varying(255))
- fee_percent (numeric, default: 0)
- tip (numeric, default: 0)

## promotions
- id (integer, NOT NULL, default: nextval('promotions_id_seq'::regclass))
- name (character varying(255), NOT NULL)
- code (character varying(25), NOT NULL)
- description (text)
- location_id (integer, NOT NULL)
- value (double precision, NOT NULL)
- type (integer, NOT NULL)
- disabled (boolean, default: FALSE)
- expires (timestamp with time zone)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- single_use (boolean, default: FALSE)
- used (boolean, default: FALSE)

## rating_categories
- id (integer, NOT NULL, default: nextval('rating_categories_id_seq'::regclass))
- label (character varying(255), NOT NULL)
- description (character varying(25), NOT NULL)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)

## rating_responses
- id (integer, NOT NULL, default: nextval('rating_responses_id_seq'::regclass))
- label (character varying(255), NOT NULL)
- description (character varying(25), NOT NULL)
- category_id (integer, NOT NULL)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)

## role_types
- id (integer, NOT NULL, default: nextval('role_types_id_seq'::regclass))
- name (text)
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)

## roles
- user_id (integer, NOT NULL)
- location_id (integer, NOT NULL)
- role_id (integer, NOT NULL)

## schema_migrations
- version (bigint, NOT NULL)
- dirty (boolean, NOT NULL)

## user_locations
- user_id (integer, NOT NULL)
- latitude (double precision, NOT NULL)
- longitude (double precision, NOT NULL)
- updated_at (timestamp with time zone)

## users
- id (integer, NOT NULL, default: nextval('users_id_seq'::regclass))
- created_at (timestamp with time zone)
- updated_at (timestamp with time zone)
- deleted_at (timestamp with time zone)
- first_name (text)
- last_name (text)
- email (text)
- picture (text)
- phone (text)
