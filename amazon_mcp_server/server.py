from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Amazon Scraper", dependencies=["mcp"])

@mcp.tool()
def search_amazon(query: str) -> str:
    """Search Amazon for products based on a query. Use this to find live e-commerce product listings and prices.
    
    Args:
        query: The search query (e.g. 'gaming mouse', 'iPhone 16')
    """
    return f"""Found the following mock products for '{query}':
1. Product: Sony WH-1000XM5 Wireless Headphones
   ASIN: B09XS7JWHH
   Price: $398.00
   Rating: 4.6 stars
   Features: Active Noise Cancellation, 30-Hour Battery Life.

2. Product: Logitech G203 Wired Gaming Mouse
   ASIN: B087LXCTFJ
   Price: $39.99
   Rating: 4.7 stars
   Features: 8,000 DPI, customizable RGB lighting.
"""

@mcp.tool()
def get_product_reviews(asin: str) -> str:
    """Get the top reviews for a specific Amazon product using its ASIN.
    
    Args:
        asin: The Amazon Standard Identification Number (ASIN)
    """
    return f"""Top mock reviews for ASIN {asin}:
- Review 1 (5 stars): "Incredible build quality. I use it every day."
- Review 2 (4 stars): "Great product, performs well but feels a little light."
- Review 3 (3 stars): "It's okay, but feels a bit fragile over time."
- Review 4 (2 stars): "Broken out of the box."
- Review 5 (5 stars): "Sturdy and reliable."
"""

if __name__ == "__main__":
    mcp.run(transport='stdio')
