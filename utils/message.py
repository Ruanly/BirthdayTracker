from discord.channel import TextChannel
from discord.errors import Forbidden, HTTPException
from discord.message import Message


async def send_message(channel: TextChannel, content=None, *, tts=False, embed=None, file=None, files=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None) -> Message | None:
    """
    Wrapper for discord.py channel.send() that handles exceptions.
    
    Returns the Message or None.
    """
    try:
        message = await channel.send(
            content=content, 
            tts=tts, 
            embed=embed, 
            file=file, 
            files=files, 
            delete_after=delete_after, 
            nonce=nonce, 
            allowed_mentions=allowed_mentions, 
            reference=reference, 
            mention_author=mention_author
        )
        return message

    except HTTPException as e:
        print(f'[{e.status} {e.response.reason}] Failed to send a message "{content}" to channel "{channel.name}".')
        
    except Forbidden as e:
        print(f'[{e.status} {e.response.reason}] Did not have permission to send a message.')

    return None