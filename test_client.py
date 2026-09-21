"""Ручная проверка клиента к Events Provider API."""

import asyncio
from datetime import date

from services.events_provider import EventsProviderClient, EventsProviderError


async def main() -> None:
    print("=== Проверка подключения к Events Provider API ===")

    async with EventsProviderClient() as client:
        print(f"Base URL: {client.base_url}")
        print(f"API key: {client.api_key[:8]}...{client.api_key[-4:]}")

        # --- 1. Список событий ---
        print("\n[1] Запрос всех событий (changed_at=2000-01-01)...")
        try:
            events = await client.fetch_events(date(2000, 1, 1))
        except EventsProviderError as e:
            print(f"ОШИБКА: {e}")
            return

        print(f"Получено событий: {len(events)}")

        if not events:
            print("Событий нет — база внешнего API пуста.")
            return

        first = events[0]
        print("\nПервое событие:")
        print(f"  id:     {first['id']}")
        print(f"  name:   {first['name']}")
        print(f"  status: {first['status']}")
        print(f"  place:  {first['place']['name']} ({first['place']['city']})")

        # --- 2. Свободные места (только для published) ---
        if first["status"] == "published":
            print(f"\n[2] Запрос мест для события {first['id'][:8]}...")
            try:
                seats = await client.fetch_seats(first["id"])
                print(f"Свободных мест: {len(seats)}")
                print(f"Первые 10: {seats[:10]}")
            except EventsProviderError as e:
                print(f"ОШИБКА при запросе мест: {e}")
        else:
            print(
                f"\n[2] Пропускаем запрос мест — статус '{first['status']}', не 'published'"
            )


if __name__ == "__main__":
    asyncio.run(main())
