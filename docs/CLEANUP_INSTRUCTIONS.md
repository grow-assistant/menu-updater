# Cleanup Instructions

As requested, all query loading now comes directly from the `database` folder instead of the example_queries module. The following files are no longer needed and can be safely deleted:

1. `prompts/example_queries.py`
2. The entire `prompts/example_queries/` directory

## Changes Made:

1. Created a centralized `load_example_queries()` function in `prompts/__init__.py` that loads queries directly from the database folder
2. Updated `google_gemini_prompt.py` and `openai_categorization_prompt.py` to use this function
3. Updated all imports in `integrate_app.py` to import from `prompts` instead of `prompts.example_queries`

## Additional Notes:

- All query examples are now loaded from the `.pgsql` files in the `database/` subdirectories
- Each query category now corresponds directly to its database folder (e.g., order_history queries come from database/order_history/*.pgsql)
- The code will now dynamically load new query examples when they're added to the database folders

## Verification:

The application should now run without any errors related to missing modules or circular imports. If you encounter any issues, please check that you've deleted the files mentioned above. 