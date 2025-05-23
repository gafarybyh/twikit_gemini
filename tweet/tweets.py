from twikit import Client, TooManyRequests, NotFound
import asyncio
import os
from datetime import datetime
from random import randint
from config import USERNAME, EMAIL, PASSWORD, MAX_RETRY, cookies_path_file, logger

# TODO* LOGIN TWITTER
async def _login_twitter():
    """
    Login to X account

    Returns:
        Client: Client instance
    """
    # Create client instance
    client = Client(language='en-US')
    
    try:
        # Check if cookies file exists and has content
        if os.path.exists(cookies_path_file) and os.path.getsize(cookies_path_file) > 0:
            # Load cookies from file
            client.load_cookies(cookies_path_file)
            print(f'{datetime.now()} - Successfully loaded cookies')
        else:
            # Login with credentials
            await client.login(
                auth_info_1=USERNAME,
                auth_info_2=EMAIL,
                password=PASSWORD
            )
            # Save cookies for future use
            client.save_cookies(cookies_path_file)
            print(f'{datetime.now()} - Login successful, cookies saved')
            
        return client
    except Exception as e:
        logger.error(f'{datetime.now()} - Error during login: {str(e)}')
        return None
    

# TODO* GET MULTIPLE PAGE TWEETS
async def _get_multiple_pages_of_tweets(search_query: str = "#btc", search_product: str = "Top", min_tweets = 30):
    """
    Get multiple pages of tweets

    Args:
        search_query (str): Search query
        search_product (str): Search product (Top, Latest, Media)
        min_tweets (int): Minimum number of tweets to return

    Returns:
        list[Tweet]: List of tweets
    """
    max_retries = MAX_RETRY
    retry_count = 0
    
    while retry_count < max_retries:
        all_tweets = []  # Reset tweets list on each retry
        
        # Login Twitter on each retry to ensure fresh connection
        twitter_client = await _login_twitter()
        
        if twitter_client is None:
            print(f'{datetime.now()} - Failed to login to X, retry {retry_count+1}/{max_retries}')
            retry_count += 1
            await asyncio.sleep(5)
            continue
        
        try:
            print(f'{datetime.now()} - Getting initial tweets...')
           
            tweets = await twitter_client.search_tweet(query=search_query, product=search_product, count=20)
            
            # Add tweets to list
            for tweet in tweets:
                all_tweets.append(tweet)
            
            print(f'{datetime.now()} - Collected {search_product} {len(all_tweets)} tweets so far')
            
            # Get next page tweets until min_tweets
            page_count = 1
            
            while len(all_tweets) < min_tweets:
                page_count += 1
                
                # Add delay to avoid rate limiting
                wait_time = randint(5, 10)
                print(f'{datetime.now()} - Waiting {wait_time} seconds before fetching page {page_count}...')
                await asyncio.sleep(wait_time)
                
                try:
                    tweets = await tweets.next()
                    
                    if not tweets or len(tweets) == 0:
                        print(f'{datetime.now()} - No more tweets available')
                        break
                    
                    # Add tweets to list
                    for tweet in tweets:
                        all_tweets.append(tweet)
                    
                    print(f'{datetime.now()} - Collected {search_product} {len(all_tweets)} tweets so far')
                    
                except TooManyRequests as e:
                    # Handle rate limiting specifically
                    wait_time = 120  # Default wait time of 2 minutes
                    if hasattr(e, 'rate_limit_reset') and e.rate_limit_reset:
                        current_time = datetime.now().timestamp()
                        wait_time = max(e.rate_limit_reset - current_time + 5, 60)
                    
                    print(f'{datetime.now()} - Rate limit exceeded. Waiting {wait_time} seconds before retrying...')
                    await asyncio.sleep(wait_time)
                    continue
                except NotFound as e:
                    print(f'{datetime.now()} - 404 Not Found error: {str(e)}')
                    # If we get a 404, we might have an invalid cursor or the search is no longer valid
                    break
                except Exception as e:
                    print(f'{datetime.now()} - Error fetching next page: {str(e)}')
                    await asyncio.sleep(10)
                    continue
            
            # If we got here, we either collected enough tweets or ran out of pages
            # Success! Return the tweets we collected
            print(f'{datetime.now()} - Successfully collected {len(all_tweets)} tweets')
            return all_tweets
            
        except TooManyRequests as e:
            wait_time = 120  # Default wait time of 2 minutes
            if hasattr(e, 'rate_limit_reset') and e.rate_limit_reset:
                current_time = datetime.now().timestamp()
                wait_time = max(e.rate_limit_reset - current_time + 5, 60)
            
            print(f'{datetime.now()} - Rate limit exceeded during initial fetch. Waiting {wait_time} seconds before retry {retry_count+1}/{max_retries}...')
            await asyncio.sleep(wait_time)
            retry_count += 1
        except NotFound as e:
            print(f'{datetime.now()} - 404 Not Found error during initial fetch: {str(e)}')
            print(f'{datetime.now()} - Waiting 10 seconds before retry {retry_count+1}/{max_retries}...')
            await asyncio.sleep(10)
            retry_count += 1
        except Exception as e:
            print(f'{datetime.now()} - Error during tweet collection: {str(e)}')
            print(f'{datetime.now()} - Waiting 10 seconds before retry {retry_count+1}/{max_retries}...')
            await asyncio.sleep(10)
            retry_count += 1
    
    # If we get here, we've exhausted all retries
    print(f'{datetime.now()} - Failed to collect tweets after {max_retries} retries')
    return all_tweets  # Return whatever we have, might be empty


# TODO* SEARCH TWEET
async def search_tweets(search_query: str, search_product: str = "Top", minimum_tweets: int = 30) -> list[dict]:
    """
    Search and get tweets from Twitter

    Args:
        search_query (str): Search query (e.g., #BTC)
        search_product (str): Search product (Top, Latest, Media)
        minimum_tweets (int): Minimum number of tweets to return

    Returns:
        list[dict]: List of tweets
    """
    
    print(f'{datetime.now()} - Searching for tweets with query: {search_query}')
    
    all_tweets = await _get_multiple_pages_of_tweets(search_query=search_query, search_product=search_product, min_tweets=minimum_tweets)
    
    if not all_tweets:
        print(f'{datetime.now()} - No tweets found for query: {search_query}')
        return []
    
    list_tweet = []
    
    for i, tweet in enumerate(all_tweets):
        tweet_count = i + 1 
        tweet_data = { 
            "tweet_count": tweet_count,
            "username": tweet.user.name,
            "text": tweet.text,
            "created_at": tweet.created_at,
            "retweets": tweet.retweet_count,
            "favorites": tweet.favorite_count
        }
        
        list_tweet.append(tweet_data)
        
    return list_tweet
