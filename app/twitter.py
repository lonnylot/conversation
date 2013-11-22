import tweepy
import app.basic
import settings

from lib import userdb

####################
### AUTH VIA TWITTER
### /auth/twitter
####################
class Auth(app.basic.BaseHandler):
  def get(self):
    consumer_key = settings.get('twitter_consumer_key')
    consumer_secret = settings.get('twitter_consumer_secret')
    callback_host = 'http://%s/twitter' % self.request.headers['host'] if settings.get('environment') != 'dev' else ''
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, callback_host)
    auth_url = auth.get_authorization_url(True)
    self.set_secure_cookie("request_token_key", auth.request_token.key)
    self.set_secure_cookie("request_token_secret", auth.request_token.secret)
    self.redirect(auth_url)

##############################
### RESPONSE FROM TWITTER AUTH
### /twitter
##############################
class Twitter(app.basic.BaseHandler):
  def get(self):
    oauth_verifier = self.get_argument('oauth_verifier', None)
    if oauth_verifier == None:
      self.render('user/twitter.html')
    else:
      consumer_key = settings.get('twitter_consumer_key')
      consumer_secret = settings.get('twitter_consumer_secret')
      auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
      auth.set_request_token(self.get_secure_cookie('request_token_key'), self.get_secure_cookie('request_token_secret'))
      auth.get_access_token(oauth_verifier)
      screen_name = auth.get_username()
      bounce_to = '/'

      access_token = {
        'secret': auth.access_token.secret,
        'user_id': '',
        'screen_name': '',
        'key': auth.access_token.key
      }

      # check if we have this user already or not in the system
      user = userdb.get_user_by_screen_name(screen_name)
      if user:
        # set the cookies based on account details
        self.set_secure_cookie("user_id_str", user['user']['id_str'])
        self.set_secure_cookie("username", user['user']['screen_name'])
        if user['email_address'] == '':
          bounce_to = '/auth/email'
      else:
        # need to create the account (so get more details from Twitter)
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        api = tweepy.API(auth)
        user = api.get_user(screen_name)
        access_token['user_id'] = user.id
        access_token['screen_name'] = user.screen_name
        user_data = {
          'auth_type': 'twitter',
          'id_str': user.id_str,
          'username': user.screen_name,
          'fullname': user.name,
          'screen_name': user.screen_name,
          'profile_image_url': user.profile_image_url,
          'profile_image_url_https': user.profile_image_url_https,
        }
        # now save to mongo
        userdb.create_new_user(user_data, access_token)
        # and set our cookies
        self.set_secure_cookie("user_id_str", user.id_str)
        self.set_secure_cookie("username", user.screen_name)
        bounce_to = '/auth/email'

      # let's save the screen_name to a cookie as well so we can use it for restricted bounces if need be
      self.set_secure_cookie('screen_name', screen_name, expires_days=30)

      # bounce to account
      self.redirect(bounce_to)
