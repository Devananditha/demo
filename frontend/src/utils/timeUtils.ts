export function tickToTime(tick: number): string {
  // 288 ticks per day (24 hours), 1 tick = 5 min, tick 0 = 00:00 (Midnight)
  // e.g. tick 96 = 8:00 AM, tick 159 = 1:15 PM, tick 192 = 4:00 PM, tick 198 = 4:30 PM, tick 204 = 5:00 PM
  const totalMinutes = tick * 5;
  const hour = Math.floor(totalMinutes / 60);
  const min = totalMinutes % 60;
  const h12 = hour % 12 === 0 ? 12 : hour % 12;
  const ampm = hour < 12 ? 'AM' : 'PM';
  return `${h12}:${min.toString().padStart(2, '0')} ${ampm}`;
}
