"""
Discord API helper with retry and rate-limit handling for send/edit operations.
"""

import asyncio
import logging
import random
from typing import Optional

import discord


logger = logging.getLogger(__name__)


class RetryPolicy:
    def __init__(self, max_attempts: int = 5, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def compute_backoff(self, attempt: int) -> float:
        # Exponential backoff with jitter
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        jitter = random.uniform(0, delay * 0.2)
        return delay + jitter


def _is_transient_http_status(status: Optional[int]) -> bool:
    if status is None:
        return False
    return status in (408, 429, 500, 502, 503, 504)


async def send_message_with_retry(
    bot: discord.Client,
    channel_id: int,
    embed: Optional[discord.Embed] = None,
    content: Optional[str] = None,
    retry: Optional[RetryPolicy] = None,
) -> bool:
    """Send a message to a channel with retry and rate-limit handling.

    Returns True on success, False otherwise.
    """
    retry = retry or RetryPolicy()
    attempts = 0

    while True:
        attempts += 1
        try:
            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"send_message_with_retry: Channel {channel_id} not found")
                return False
            await channel.send(content=content, embed=embed)
            return True
        except discord.Forbidden:
            logger.error(f"send_message_with_retry: Forbidden to send to channel {channel_id}")
            return False
        except discord.NotFound:
            logger.error(f"send_message_with_retry: Channel {channel_id} not found (404)")
            return False
        except discord.HTTPException as e:
            status = getattr(e, 'status', None)
            retry_after = None
            try:
                if hasattr(e, 'response') and e.response and hasattr(e.response, 'headers'):
                    retry_after = e.response.headers.get('Retry-After')
            except Exception:
                retry_after = None

            if status == 429 and retry_after:
                try:
                    sleep_for = float(retry_after)
                except ValueError:
                    sleep_for = retry.compute_backoff(attempts)
                logger.warning(f"Rate limited (429). Sleeping for {sleep_for:.2f}s before retry (attempt {attempts}/{retry.max_attempts})")
                await asyncio.sleep(sleep_for)
            elif _is_transient_http_status(status) and attempts < retry.max_attempts:
                sleep_for = retry.compute_backoff(attempts)
                logger.warning(f"Transient Discord error {status}. Retrying in {sleep_for:.2f}s (attempt {attempts}/{retry.max_attempts})")
                await asyncio.sleep(sleep_for)
            else:
                logger.error(f"send_message_with_retry failed with HTTPException: status={status}, attempts={attempts}")
                return False
        except Exception as e:
            logger.error(f"send_message_with_retry unexpected error: {e}")
            return False


async def edit_channel_name_with_retry(
    bot: discord.Client,
    channel_id: int,
    new_name: str,
    retry: Optional[RetryPolicy] = None,
) -> bool:
    """Edit a channel's name with retry and rate-limit handling.

    Returns True on success, False otherwise.
    """
    retry = retry or RetryPolicy()
    attempts = 0

    while True:
        attempts += 1
        try:
            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"edit_channel_name_with_retry: Channel {channel_id} not found")
                return False
            await channel.edit(name=new_name)
            return True
        except discord.Forbidden:
            logger.error(f"edit_channel_name_with_retry: Forbidden to edit channel {channel_id}")
            return False
        except discord.NotFound:
            logger.error(f"edit_channel_name_with_retry: Channel {channel_id} not found (404)")
            return False
        except discord.HTTPException as e:
            status = getattr(e, 'status', None)
            retry_after = None
            try:
                if hasattr(e, 'response') and e.response and hasattr(e.response, 'headers'):
                    retry_after = e.response.headers.get('Retry-After')
            except Exception:
                retry_after = None

            if status == 429 and retry_after:
                try:
                    sleep_for = float(retry_after)
                except ValueError:
                    sleep_for = retry.compute_backoff(attempts)
                logger.warning(f"Rate limited (429). Sleeping for {sleep_for:.2f}s before retry (attempt {attempts}/{retry.max_attempts})")
                await asyncio.sleep(sleep_for)
            elif _is_transient_http_status(status) and attempts < retry.max_attempts:
                sleep_for = retry.compute_backoff(attempts)
                logger.warning(f"Transient Discord error {status}. Retrying in {sleep_for:.2f}s (attempt {attempts}/{retry.max_attempts})")
                await asyncio.sleep(sleep_for)
            else:
                logger.error(f"edit_channel_name_with_retry failed with HTTPException: status={status}, attempts={attempts}")
                return False
        except Exception as e:
            logger.error(f"edit_channel_name_with_retry unexpected error: {e}")
            return False


