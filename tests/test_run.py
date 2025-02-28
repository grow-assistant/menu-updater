import main

if __name__ == "__main__":
    print("Starting the application...")
    try:
        main.run_langchain_streamlit_app()
        print("Application started successfully!")
    except Exception as e:
        print(f"Error starting application: {str(e)}") 