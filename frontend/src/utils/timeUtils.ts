export function tickToTime(tick: number): string {
  // Tick 0 = 8:00 AM, 1 tick = 5 min
  const totalMinutes = tick * 5;
  const hour = Math.floor(totalMinutes / 60) + 8;
  const min = totalMinutes % 60;
  const h12 = hour % 12 === 0 ? 12 : hour % 12;
  const ampm = hour < 12 ? 'AM' : 'PM';
  return `${h12}:${min.toString().padStart(2, '0')} ${ampm}`;
}
