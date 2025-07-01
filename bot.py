import os
import logging
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from sqlalchemy.orm import Session
from models import QueueSlot, User, Branch, Organization
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_ID

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        try:
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
            self.chat_id = TELEGRAM_GROUP_ID
            logger.info("TelegramNotifier успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации TelegramNotifier: {e}")
            raise

    async def send_booking_notification(self, slot: QueueSlot, db_session: Session):
        try:
            user = db_session.query(User).filter(User.id == slot.user_id).first()
            branch = db_session.query(Branch).filter(Branch.id == slot.branch_id).first()
            
            if not user:
                logger.error(f"Пользователь с ID {slot.user_id} не найден")
                return
            if not branch:
                logger.error(f"Филиал с ID {slot.branch_id} не найден")
                return
                
            organization = db_session.query(Organization).filter(
                Organization.id == branch.organization_id
            ).first()
            
            org_name = organization.name if organization else "Неизвестная организация"

            message = (
                "📅 Новая запись создана!\n\n"
                f"👤 Пользователь: {user.full_name or 'Не указано'}\n"
                f"📧 Email: {user.email}\n"
                f"📌 Филиал: {branch.name}\n"
                f"🏢 Организация: {org_name}\n"
                f"📍 Адрес: {branch.address or 'Не указан'}\n"
                f"📅 Дата: {slot.date}\n"
                f"⏰ Время: {slot.time}\n"
                f"🔢 Номер записи: {slot.id}\n"
                f"🔹 Статус: {slot.status}"
            )

            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown"
            )
            logger.info(f"Уведомление о записи {slot.id} отправлено в группу {self.chat_id}")
            
        except TelegramError as e:
            logger.error(f"Ошибка Telegram при отправке уведомления: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}", exc_info=True)

    async def send_admin_notification(self, message: str):
        """
        Отправляет произвольное сообщение администратору
        
        :param message: Текст сообщения
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"⚠️ Админ-уведомление:\n\n{message}"
            )
            logger.info("Админ-уведомление отправлено")
        except Exception as e:
            logger.error(f"Ошибка отправки админ-уведомления: {e}")

try:
    telegram_notifier = TelegramNotifier()
except Exception as e:
    logger.critical(f"Не удалось инициализировать TelegramNotifier: {e}")
    telegram_notifier = None

if __name__ == "__main__":
    import asyncio
    from database import SessionLocal
    
    async def test_notification():
        db = SessionLocal()
        try:
            test_slot = QueueSlot(
                id=999,
                branch_id=1,
                user_id=1,
                date="2023-12-31",
                time="15:00",
                status="забронирован"
            )
            
            if telegram_notifier:
                await telegram_notifier.send_booking_notification(test_slot, db)
            else:
                print("TelegramNotifier не инициализирован")
        finally:
            db.close()
    
    asyncio.run(test_notification())