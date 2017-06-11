__author__ = 'SmileyBarry'

from .core import APIConnection, SteamObject, StoreAPIConnection, store
from .decorators import cached_property, INFINITE


class SteamApp(SteamObject):
    def __init__(self, appid, name=None, owner=None):
        self._id = appid
        if name is not None:
            import time
            self._cache = dict()
            self._cache['name'] = (name, time.time())
        # Normally, the associated userid is also the owner.
        # That would not be the case if the game is borrowed, though. In that case, the object creator
        # usually defines attributes accordingly. However, at this time we can't ask the API "is this
        # game borrowed?", unless it's the actively-played game, so this distinction isn't done in the
        # object's context, but in the object creator's context.
        self._owner = owner
        self._userid = self._owner

    # Factory methods
    @staticmethod
    def from_api_response(api_json, associated_userid=None):
        """
        Create a new SteamApp instance from an APIResponse object.

        :param api_json: The raw JSON returned by the API, in "APIResponse" form.
        :type api_json: steamapi.core.APIResponse
        :param associated_userid: A user ID associated to this game, if applicable. This can be the user who played the
                                  app/game, or its owner if it is borrowed, depending on context.
        :type associated_userid: long
        :return: a new SteamApp instance
        :rtype: SteamApp
        """
        if 'appid' not in api_json:
            # An app ID is a bare minimum.
            raise ValueError("An app ID is required to create a SteamApp object.")

        appid = api_json.appid
        name = None
        if 'name' in api_json:
            name = api_json.name

        return SteamApp(appid, name, associated_userid)

    @cached_property(ttl=INFINITE)
    def _schema(self):
        return APIConnection().call("ISteamUserStats", "GetSchemaForGame", "v2", appid=self._id)

    @property
    def appid(self):
        return self._id

    @cached_property(ttl=INFINITE)
    def achievements(self):
        global_percentages = APIConnection().call("ISteamUserStats", "GetGlobalAchievementPercentagesForApp", "v0002",
                                                  gameid=self._id)
        if self._userid is not None:
            # Ah-ha, this game is associated to a user!
            userid = self._userid
            unlocks = APIConnection().call("ISteamUserStats",
                                           "GetUserStatsForGame",
                                           "v2",
                                           appid=self._id,
                                           steamid=userid)
            if 'achievements' in unlocks.playerstats:
                unlocks = [associated_achievement.name
                           for associated_achievement in unlocks.playerstats.achievements
                           if associated_achievement.achieved != 0]
        else:
            userid = None
            unlocks = None
        achievements_list = []
        if 'availableGameStats' not in self._schema.game:
            # No stat data -- at all. This is a hidden app.
            return achievements_list
        for achievement in self._schema.game.availableGameStats.achievements:
            achievement_obj = SteamAchievement(self._id, achievement.name, achievement.displayName, userid)
            achievement_obj._cache = {}
            if achievement.hidden == 0:
                store(achievement_obj, "is_hidden", False)
            else:
                store(achievement_obj, "is_hidden", True)
            for global_achievement in global_percentages.achievementpercentages.achievements:
                if global_achievement.name == achievement.name:
                    achievement_obj.unlock_percentage = global_achievement.percent
            achievements_list += [achievement_obj]
        if unlocks is not None:
            for achievement in achievements_list:
                if achievement.apiname in unlocks:
                    store(achievement, "is_achieved", True)
                else:
                    store(achievement, "is_achieved", False)
        return achievements_list

    @cached_property(ttl=INFINITE)
    def name(self):
        if 'gameName' in self._schema.game:
            return self._schema.game.gameName
        else:
            return "<Unknown>"

    @cached_property(ttl=INFINITE)
    def owner(self):
        if self._owner is None:
            return self._userid
        else:
            return self._owner

    @cached_property(ttl=INFINITE)
    def app_info(self):
        response = StoreAPIConnection().call("appdetails", appids=self._id, filters="basic,fullgame,developers," +
                                                                                    "publishers,demos,price_overview," +
                                                                                    "platforms,metacritic,categories," +
                                                                                    "genres,recommendations," +
                                                                                    "release_date")
        if response[str(self._id)].success:
            return response[str(self._id)].data

    @property
    def type(self):
        """ Either 'game', 'movie' or 'demo'. More values could be possible.  """
        if self.app_info:
            return self.app_info.type

    @property
    def required_age(self):
        """ Minimum age to access SteamApp. """
        if self.app_info:
            return self.app_info.required_age

    @property
    def dlc(self):
        """ List the appids of the SteamApp's DLCs. """
        #TODO: Return list of SteamApps instead of list of ids
        if self.app_info:
            return self.app_info.dlc

    @property
    def detailed_description(self):
        """ Detailed unicode description of SteamApp in html. """
        if self.app_info:
            return self.app_info.detailed_description

    @property
    def about_the_game(self):
        """ Short unicode description of SteamApp in html. """
        if self.app_info:
            return self.app_info.about_the_game

    @property
    def supported_languages(self):
        """ Returns an html unicode string describing available languages. """
        #TODO: Translate html into a more user friendly format
        if self.app_info:
            return self.app_info.supported_languages

    @property
    def header_image(self):
        """ Link to the header image of the SteamApp. """
        if self.app_info:
            return self.app_info.header_image

    @property
    def legal_notice(self):
        """ Legal notice attached to the SteamApp. """
        if self.app_info:
            return self.app_info.legal_notice

    @property
    def website(self):
        """ Link to the SteamApp's website. """
        if self.app_info:
            return self.app_info.website

    @property
    def pc_requirements(self):
        """
        Dictionary describing PC requirements to run SteamApp.
            recommended: Html string describing recommended requirements
            minimunm: Html string describing minimal requirements
        """
        if self.app_info:
            return self.app_info.pc_requirements

    @property
    def mac_requirements(self):
        """
        Dictionary describing Mac requirements to run SteamApp.
            recommended: Html string describing recommended requirements
            minimunm: Html string describing minimal requirements
        """
        if self.app_info:
            return self.app_info.mac_requirements

    @property
    def linux_requirements(self):
        """
        Dictionary describing linux requirements to run SteamApp.
            recommended: Html string describing recommended requirements
            minimunm: Html string describing minimal requirements
        """
        if self.app_info:
            return self.app_info.linux_requirements

    @property
    def fullgame(self):
        """ Steam id of fullgame if current SteamApp is a demo. """
        if self.app_info:
            return self.app_info.fullgame

    @property
    def developers(self):
        """ List of SteamApp's developers. """
        if self.app_info:
            return self.app_info.developers

    @property
    def publishers(self):
        """ List of SteamApp's publishers. """
        if self.app_info:
            return self.app_info.publishers

    @property
    def demos(self):
        """
        Information about the SteamApp's demo. None if there is none.
            appid: appid of the demo app
            description: Used to note the demo's restrictions
        """
        #TODO: Return a SteamApp instead of the demo's appid
        if self.app_info:
            return self.app_info.demos

    @property
    def price_overview(self):
        """
        Information about the SteamApp's demo. None if free-to-play.
            currency: Currency prices are noted in.
            initial: Pre-discount price
            final: Discounted price
            discount_percent
        """
        if self.app_info:
            return self.app_info.price_overview

    @property
    def platforms(self):
        """
        Booleans indicating whether SteamApp is available on platform.
            windows
            mac
            linux
        """
        if self.app_info:
            return self.app_info.platforms

    @property
    def metacritic(self):
        """
        Information about SteamApp's metacritic score. None if there is no score.
            score
            url: Url to metacritic page.
        """
        if self.app_info:
            return self.app_info.metacritic

    @property
    def categories(self):
        """
        List of the categories the SteamApp belongs to.
            id: An integer associated with the category
            description: Short description of the category
        """
        #TODO: Transform into a list of descriptions.
        if self.app_info:
            return self.app_info.categories

    @property
    def genres(self):
        """
        List of the categories the SteamApp belongs to.
            id: An integer associated with the genre
            description: Short description of the genre
        """
        #TODO: Transform into a list of descriptions.
        if self.app_info:
            return self.app_info.genres

    @property
    def recommendations(self):
        """
        Information related to the SteamApp recommendations
            total : integer
        """
        if self.app_info:
            return self.app_info.recommendations

    @property
    def release_date(self):
        """
        Information related to the SteamApp's release date.
            coming_soon: True if unreleased, False otherwise
            date: Date string formatted according to cc parameter. Empty when unreleased.
        """
        if self.app_info:
            return self.app_info.release_date

    def __str__(self):
        return self.name

    def __hash__(self):
        # Don't just use the ID so ID collision between different types of objects wouldn't cause a match.
        return hash(('app', self.id))


class SteamAchievement(SteamObject):
    def __init__(self, linked_appid, apiname, displayname, linked_userid=None):
        """
        Initialise a new instance of SteamAchievement. You shouldn't create one yourself, but from
        "SteamApp.achievements" instead.

        :param linked_appid: The AppID associated with this achievement.
        :type linked_appid: int
        :param apiname: The API-based name of this achievement. Usually a string.
        :type apiname: str or unicode
        :param displayname: The achievement's user-facing name.
        :type displayname: str or unicode
        :param linked_userid: The user ID this achievement is linked to.
        :type linked_userid: int
        :return: A new SteamAchievement instance.
        """
        self._appid = linked_appid
        self._id = apiname
        self._displayname = displayname
        self._userid = linked_userid
        self.unlock_percentage = 0.0

    def __hash__(self):
        # Don't just use the ID so ID collision between different types of objects wouldn't cause a match.
        return hash((self.id, self._appid))

    @property
    def appid(self):
        return self._appid

    @property
    def name(self):
        return self._displayname

    @property
    def apiname(self):
        return self._id

    @cached_property(ttl=INFINITE)
    def is_hidden(self):
        response = APIConnection().call("ISteamUserStats",
                                        "GetSchemaForGame",
                                        "v2",
                                        appid=self._appid)
        for achievement in response.game.availableGameStats.achievements:
            if achievement.name == self._id:
                if achievement.hidden == 0:
                    return False
                else:
                    return True

    @cached_property(ttl=INFINITE)
    def is_unlocked(self):
        if self._userid is None:
            raise ValueError("No Steam ID linked to this achievement!")
        response = APIConnection().call("ISteamUserStats",
                                        "GetPlayerAchievements",
                                        "v1",
                                        steamid=self._userid,
                                        appid=self._appid,
                                        l="English")
        for achievement in response.playerstats.achievements:
            if achievement.apiname == self._id:
                if achievement.achieved == 1:
                    return True
                else:
                    return False
        # Cannot be found.
        return False
