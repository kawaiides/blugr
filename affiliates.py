import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def resolve_affiliate_link(affiliate_url):
    try:
        # Resolve redirects to get final URL
        response = requests.get(affiliate_url, allow_redirects=True, timeout=10)
        final_url = response.url
        return final_url
    except Exception as e:
        raise ValueError(f"Error resolving affiliate link: {str(e)}")

def extract_product_info(product_url):
    product_details = {}
    try:
        # specifying user agent, You can use other user agents
        # available on the internet
        HEADERS = ({
            "User-Agent":'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)Chrome/44.0.2403.157 Safari/537.36',
            'Accept-Language': 'en-US, en;q=0.5'
        })
        print('get req')
        # Making the HTTP Request
        webpage = requests.get(product_url, headers=HEADERS)
        # Creating the Soup Object containing all data
        soup = BeautifulSoup(webpage.content, "lxml")

        # retrieving product title
        try:
            # Outer Tag Object
            title = soup.find("span", 
                            attrs={"id": 'productTitle'})

            # Inner NavigableString Object
            title_value = title.string

            # Title as a string value
            title_string = title_value.strip().replace(',', '')

        except AttributeError:
            title_string = "NA"

        # retrieving price
        try:
            price = soup.find(
                "span", attrs={'id': 'priceblock_ourprice'}).string.strip().replace(',', '')
            # we are omitting unnecessary spaces
            # and commas form our string
        except AttributeError:
            price = "NA"

        # retrieving product rating
        try:
            rating = soup.find("i", attrs={
                            'class': 'a-icon a-icon-star a-star-4-5'}).string.strip().replace(',', '')

        except AttributeError:

            try:
                rating = soup.find(
                    "span", attrs={'class': 'a-icon-alt'}).string.strip().replace(',', '')
            except:
                rating = "NA"

        try:
            review_count = soup.find(
                "span", attrs={'id': 'acrCustomerReviewText'}).string.strip().replace(',', '')

        except AttributeError:
            review_count = "NA"

        # print availablility status
        try:
            available = soup.find("div", attrs={'id': 'availability'})
            available = available.find("span").string.strip().replace(',', '')

        except AttributeError:
            available = "NA"
        
        try:
            image_wrapper = soup.find("div", {"id": "imgTagWrapperId"})
            image_element = image_wrapper.find("img")
            image_url = image_element.get('src') or image_element.get('data-old-hires')
        except AttributeError:
            try:
                image_element = soup.find("img", {"id": "landingImage"})
                image_url = image_element.get('src')
            except:
                image_url = "NA"
        
        product_details = {
            'title': title_string,
            'price': price,
            'available': available,
            'review_count': review_count,
            'product_url': product_url,
            'image_url': image_url
        }
        print(product_details)
        return product_details
    
    except Exception as e:
        raise ValueError(f"Error extracting product info: {str(e)}")