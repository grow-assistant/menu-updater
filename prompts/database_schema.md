# Database Schema Documentation

## User Management
### users
- Primary key: `id`
- Core fields: `first_name`, `last_name`, `email`, `phone`, `picture`
- Timestamps: `created_at`, `updated_at`, `deleted_at`

### identities (OAuth/External Auth)
- Primary key: `id`
- Foreign keys: `user_id -> users.id`
- Core fields: `provider`, `uid`, `picture`

### device_sessions
- Primary key: `id`
- Foreign keys: `user_id -> users.id`
- Core fields: `device_token`, `device_type`, `expires_at`

### roles (Junction Table)
- Composite key: (`user_id`, `location_id`, `role_id`)
- Foreign keys:
  - `user_id -> users.id`
  - `location_id -> locations.id`
  - `role_id -> role_types.id`

### role_types
- Primary key: `id`
- Core fields: `name`

## Location Management
### locations
- Primary key: `id`
- Core fields: `name`, `description`, `timezone`, `latitude`, `longitude`, `code`, `tax_rate`, `settings`
- Flags: `active`, `disabled`

### location_hours
- Primary key: `id`
- Foreign keys: `location_id -> locations.id`
- Core fields: `day_of_week`, `time_slot`, `open_time`, `close_time`

### markers
- Primary key: `id`
- Foreign keys: `location_id -> locations.id`
- Core fields: `name`, `disabled`

### api_keys
- Primary key: `id`
- Foreign keys: `location_id -> locations.id`
- Core fields: `api_key`, `name`

### indicators
- Primary key: `id`
- Foreign keys: 
  - `location_id -> locations.id`
  - `api_key_id -> api_keys.id`
- Core fields: `name`, `uid`, `status`, `version`, `last_contact`

## Menu Structure
### menus
- Primary key: `id`
- Foreign keys: `location_id -> locations.id`
- Core fields: `name`, `description`, `disabled`

### categories
- Primary key: `id`
- Foreign keys: `menu_id -> menus.id`
- Core fields: `name`, `description`, `disabled`, `start_time`, `end_time`, `seq_num`

### items
- Primary key: `id`
- Foreign keys: `category_id -> categories.id`
- Core fields: `name`, `description`, `price`, `disabled`, `seq_num`

### options
- Primary key: `id`
- Foreign keys: `item_id -> items.id`
- Core fields: `name`, `description`, `min`, `max`, `disabled`

### option_items
- Primary key: `id`
- Foreign keys: `option_id -> options.id`
- Core fields: `name`, `description`, `price`, `disabled`

## Order Management
### orders
- Primary key: `id`
- Foreign keys:
  - `customer_id -> users.id`
  - `vendor_id -> users.id`
  - `location_id -> locations.id`
  - `marker_id -> markers.id`
- Core fields: `status`, `total`, `tax`, `instructions`, `type`, `fee`, `fee_percent`, `tip`, `loyalty_id`

### order_items
- Primary key: `id`
- Foreign keys:
  - `order_id -> orders.id`
  - `item_id -> items.id`
- Core fields: `quantity`, `instructions`

### order_option_items
- Primary key: `id`
- Foreign keys:
  - `order_id -> orders.id`
  - `order_item_id -> order_items.id`
  - `option_item_id -> option_items.id`

### messages
- Primary key: `id`
- Foreign keys:
  - `sender_id -> users.id`
  - `recipient_id -> users.id`
  - `order_id -> orders.id`
- Core fields: `content`, `read`

## Promotions & Discounts
### promotions
- Primary key: `id`
- Foreign keys: `location_id -> locations.id`
- Core fields: `name`, `code`, `description`, `value`, `type`, `disabled`, `expires`, `single_use`, `used`

### discounts
- Primary key: `id`
- Foreign keys:
  - `order_id -> orders.id`
  - `user_id -> users.id`
- Core fields: `amount`, `reason`

## Rating System
### order_ratings
- Primary key: `id`
- Foreign keys: `order_id -> orders.id`
- Core fields: `acknowledged`
- Usage notes: Base table that indicates an order has been rated. Always LEFT JOIN from orders to this table.

### rating_categories
- Primary key: `id`
- Core fields: `label`, `description`
- Common values: 'How was your service?', 'How was your order experience?', 'How was your food?'

### rating_responses
- Primary key: `id`
- Foreign keys: `category_id -> rating_categories.id`
- Core fields: `label`, `description`

### order_ratings_feedback
- Primary key: `id`
- Foreign keys:
  - `rating_id -> order_ratings.id`
  - `category_id -> rating_categories.id`
- Core fields: `value` (1-5 rating), `notes` (text feedback)
- Usage notes: Contains the actual rating values. Always LEFT JOIN from order_ratings to this table.

### order_ratings_feedback_responses
- Primary key: `id`
- Foreign keys:
  - `feedback_id -> order_ratings_feedback.id`
  - `response_id -> rating_responses.id`
- Usage notes: Contains specific response options selected by customers for their ratings.

## Relationships Summary
- A user can have multiple identities and device sessions (1->*)
- A location can have multiple menus, markers, and API keys (1->*)
- A menu contains multiple categories (1->*)
- A category contains multiple items (1->*)
- An item can have multiple options (1->*)
- An option can have multiple option items (1->*)
- An order belongs to a customer and vendor (both users) and contains multiple order items (1->*)
- Order items can have multiple option items through order_option_items (*->*)
- Orders can have multiple ratings and messages (1->*)