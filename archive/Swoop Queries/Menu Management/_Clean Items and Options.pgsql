
SELECT setval(pg_get_serial_sequence('public.items', 'id'), (SELECT MAX(id) FROM public.items) + 1);
SELECT setval(pg_get_serial_sequence('public.options', 'id'), (SELECT MAX(id) FROM public.options) + 1);
SELECT setval(pg_get_serial_sequence('public.option_items', 'id'), (SELECT MAX(id) FROM public.option_items) + 1);