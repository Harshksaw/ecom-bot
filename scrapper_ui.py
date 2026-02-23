
import streamlit as st
from prod_assistant.etl.data_ingestion import DataIngestion
from prod_assistant.etl.data_scrapper import BooksToScrapeScraper
import os

scraper = BooksToScrapeScraper()
output_path = "data/product_reviews.csv"

st.title("📚 Books to Scrape (Educational)")
st.info("ℹ️ Scraping from **books.toscrape.com** - a safe sandbox for testing.")

# Fetch categories on load
if "categories" not in st.session_state:
    with st.spinner("Fetching categories..."):
        cats = scraper.get_categories()
        st.session_state.categories = [c["name"] for c in cats]

selected_category = st.selectbox(
    "Select a Category to Scrape", 
    ["All"] + st.session_state.categories if "categories" in st.session_state else []
)

max_books = st.slider("How many books to scrape?", min_value=1, max_value=50, value=5)

if st.button("🚀 Start Scraping"):
    if not selected_category:
        st.warning("⚠️ Please select a category.")
    else:
        st.write(f"🔍 Scraping category: **{selected_category}**")
        
        # Scraper callback to update UI
        status_placeholder = st.empty()
        def status_callback(msg, _):
            status_placeholder.info(msg)
            
        if selected_category == "All":
             # iterating all categories logic would go here, for now just show warning
             st.warning("All categories scraping not fully implemented in UI demo. Please pick a specific category.")
             books = []
        else:
            books = scraper.scrape_category(selected_category, max_books=max_books, status_callback=status_callback)
        
        if books:
            scraper.save_to_csv(books, output_path)
            st.session_state["scraped_data"] = books
            
            st.success(f"✅ Scraped {len(books)} books!")
            st.dataframe(books)
            st.download_button("📥 Download CSV", data=open(output_path, "rb"), file_name="books_data.csv")
        else:
            st.error("❌ No books found or error occurred.")

if "scraped_data" in st.session_state and st.button("🧠 Store in Vector DB (AstraDB)"):
    with st.spinner("📡 Initializing ingestion pipeline..."):
        try:
            ingestion = DataIngestion()
            st.info("🚀 Running ingestion pipeline...")
            ingestion.run_pipeline()
            st.success("✅ Data successfully ingested to AstraDB!")
        except Exception as e:
            st.error("❌ Ingestion failed!")
            st.exception(e)