import os
import discord

from datetime import datetime, timedelta
from discord.ext import commands, tasks
from dotenv import load_dotenv
from utils.database import DatabaseConnection
from utils.message import send_message


# Lookup for months by index
MONTHS = [
    'January', 
    'February', 
    'March', 
    'April', 
    'May',
    'June', 
    'July', 
    'August', 
    'September', 
    'October', 
    'November', 
    'December'
]


# Create the bot
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)


# Confirm the bot is live
@bot.event
async def on_ready():
    
    # Do some initializations
    load_references(bot)
    check_birthday.start()

    # Create the table
    with DatabaseConnection(bot.database_url) as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS data (id bigint PRIMARY KEY, month int, day int, celebrated bool);")

    # Verify that everything worked
    print('Bot is online.')


# Send an initial message
@bot.event
async def on_member_join(member):

    # Create the dm channel
    if member.dm_channel is None:
        await member.create_dm()

    # Send the dm
    dm = member.dm_channel
    await dm.send(bot.welcome_message)


# Set birthday in database based on dm
@bot.event
async def on_message(message):
    # Get the channel that the message was sent in
    channel = message.channel

    # Get the member that sent the message
    member = bot.guild.get_member(message.author.id)
    if member is None:
        return

    # Return if this is not a dm, or if the author is the bot
    if not isinstance(channel, discord.channel.DMChannel) or member.bot:
        return

    # Split the text into arguments
    args = message.content.split(' ')

    # Check if the right number of arguments (3) was provided
    if len(args) != 3:
        return

    # Check if the first argument indicates the member wants to set their birthday
    if args[0].lower() != 'birthday':
        return
    
    # See if the month was written as text
    if (capitalized := args[1].capitalize()) in MONTHS:
        month = MONTHS.index(capitalized)+1
    else:
        month = None

    # Convert the argument for day
    try:
        day = int(args[2])

        # Convert the argument for month if it was passed as a number instead
        if month is None:
            month = int(args[1])
    
    # Tell the user if the arguments could not be parsed
    except ValueError:
        await send_message(channel, f'I could not parse the month "{args[1]}" or the day "{args[2]}".')
        return

    # Check if the day is valid
    try:
        datetime(2004, month, day) # Testing on 2004 allows leap-day birthdays
    except ValueError:
        await send_message(channel, f'The month "{args[1]}" and day "{args[2]}" do not make a valid birthday.')
        return

    # Add the day and month into the database
    ID = member.id
    with DatabaseConnection(bot.database_url) as cursor:
        
        cursor.execute("SELECT * FROM data WHERE id=%s", (ID,))
        if cursor.fetchone() is None:

            cursor.execute("INSERT INTO data VALUES (%s, %s, %s, %s)", (ID, month, day, False))
        else:
            cursor.execute("UPDATE data SET month=%s, day=%s, celebrated=%s WHERE id=%s", (month, day, False, ID))


    await send_message(channel, 'Your birthday was successfully recorded!')
    await send_message(bot.staff_channel, f'{member.nick or member.name} has recorded the birthday ({MONTHS[month-1]} {day})')


@tasks.loop(hours=24)
async def check_anniversary(): 

    now = datetime.utcnow()

    with DatabaseConnection(bot.database_url) as cursor:

        for member in bot.guild.members:

            if member is None:
                continue
            
            temp = member.joined_at
            years = 0

            while temp <= (now - timedelta(days=182)):
                temp += timedelta(days=182)
                years += 0.5
            
            if years == 0:
                continue
            if temp.days != 0:
                continue

            cursor.execute("SELECT * FROM data WHERE id=%s", (member.id,))
            data = cursor.fetchone()

            birthday_month = data[1]
            birthday_day = data[2]
            try:
                birthday = datetime(now.year, birthday_month, birthday_day)
            except ValueError as e:
                birthday_day = 28
                birthday = datetime(now.year, birthday_month, birthday_day)
                print(e)
            
            if data is None:
                await send_message(bot.member_channel, 
                    bot.anniversary_message_one.replace('NAME', f'{member.mention}'))
                continue

            if birthday < now - timedelta(months=6):
                await send_message(bot.member_channel, 
                    bot.anniversary_message_one.replace('NAME', f'{member.mention}')).replace('XXX', f"{years:.1f} years")
            else:
                await send_message(bot.member_channel, 
                    bot.anniversary_message_two.replace('NAME', f'{member.mention}')).replace('XXX', f"{years:.1f} years")

# Check for birthdays every day
@tasks.loop(hours=24)
async def check_birthday(): 
    # Get the current date, and the future date used to check upcoming birthdays
    now = datetime.utcnow()
    ahead_date = now + timedelta(days=bot.ahead_range)

    # Open the database connection
    with DatabaseConnection(bot.database_url) as cursor:
        
        # Get the data
        cursor.execute("SELECT * FROM data")
        data = cursor.fetchall()
        
        if data is None:
            return

        # Loop through all recorded birthdays
        for datapoint in data:

            # Get the recorded birthday day and month
            birthday_month = datapoint[1]
            birthday_day = datapoint[2]
            already_celebrated = datapoint[3]

            # Change leap day birthdays to 28 on non-leap years
            try:
                datetime(now.year, birthday_month, birthday_day)
            except ValueError as e:
                birthday_day = 28
                print(e)
            
            # Get the member
            member = bot.guild.get_member(datapoint[0])
            if member is None:
                continue

            # Check if the birthday is today
            if now.day == birthday_day and now.month == birthday_month:

                # Only send if the birthday has not already been celebrated
                if not already_celebrated:            
                    
                    await send_message(bot.staff_channel, 
                        f'Today is {member.nick or member.name}\'s Birthday!')

                    if member.joined_at < (now - timedelta(days=182)):
                        await send_message(bot.member_channel, 
                            bot.birthday_message_one.replace('NAME', f'{member.mention}'))
                    else:
                        await send_message(bot.member_channel, 
                            bot.birthday_message_two.replace('NAME', f'{member.mention}'))

                    already_celebrated = True
            else:
                already_celebrated = False

            # Tell the database that the birthday has been celebrated
            with DatabaseConnection(bot.database_url) as cursor:
                cursor.execute("UPDATE data SET celebrated=%s WHERE id=%s", (already_celebrated, member.id))


            # Check if the birthday is upcoming
            if ahead_date.day == birthday_day and ahead_date.month == birthday_month:

                await send_message(bot.staff_channel, 
                    f'{member.nick or member.name}\'s birthday is in {bot.ahead_range} days!')


def load_references(bot):
    """Retrieves the guild, channels, and birthday message and stores them as fields of the bot."""
    # Get the guild
    bot.guild = bot.get_guild(int(os.environ.get('GUILD_ID')))
    if bot.guild is None:
        print('Failed to find the guild.')
        exit()

    # Get the channels
    bot.staff_channel = bot.guild.get_channel(int(os.environ.get('STAFF_CHANNEL')))
    if bot.staff_channel is None:
        print('Failed to find the staff channel.')
        exit()

    bot.member_channel = bot.guild.get_channel(int(os.environ.get('MEMBER_CHANNEL')))
    if bot.member_channel is None:
        print('Failed to find the member channel.')
        exit()

    # Get the birthday message
    bot.birthday_message_one = os.environ.get('BIRTHDAY_MESSAGE_1')
    if bot.birthday_message_one is None:
        print('Failed to get the birthday message 1')
        exit()

     # Get the birthday message
    bot.birthday_message_two = os.environ.get('BIRTHDAY_MESSAGE_2')
    if bot.birthday_message_two is None:
        print('Failed to get the birthday message 2')
        exit()

    # Get the birthday message
    bot.birthday_anniversary_one = os.environ.get('ANNIVERSARY_MESSAGE_1')
    if bot.birthday_anniversary_one is None:
        print('Failed to get the anniversary message 1')
        exit()

     # Get the birthday message
    bot.birthday_anniversary_two = os.environ.get('ANNIVERSARY_MESSAGE_2')
    if bot.birthday_anniversary_two is None:
        print('Failed to get the anniversary message 2')
        exit()

    # Get the welcome message
    bot.welcome_message = os.environ.get('WELCOME_MESSAGE')
    if bot.welcome_message is None:
        print('Failed to get the welcome message')
        exit()

    # Get the ahead range
    bot.ahead_range = int(os.environ.get('ALERT_DAYS'))
    if bot.ahead_range is None:
        print('Failed to get the ahead range.')
        exit()

    # Get the database url
    bot.database_url = os.environ.get('DATABASE_URL')
    if bot.database_url is None:
        print('Failed to get the database')
        exit()


if __name__ == '__main__':
    # Load .env file
    load_dotenv()

    # Run Bot
    bot.run(os.environ.get('BOT_TOKEN'))
