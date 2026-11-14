function formatDateForCalendar(dateString) {
  if (!dateString) {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${year}${month}${day}`;
  }

  const parsedDate = new Date(dateString);
  if (isNaN(parsedDate.getTime())) {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${year}${month}${day}`;
  }

  const year = parsedDate.getFullYear();
  const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
  const day = String(parsedDate.getDate()).padStart(2, "0");
  return `${year}${month}${day}`;
}

function getNextDayFormatted(dateFormatted) {
  const year = parseInt(dateFormatted.substring(0, 4), 10);
  const month = parseInt(dateFormatted.substring(4, 6), 10) - 1;
  const day = parseInt(dateFormatted.substring(6, 8), 10);

  const nextDay = new Date(year, month, day + 1);
  const nextYear = nextDay.getFullYear();
  const nextMonth = String(nextDay.getMonth() + 1).padStart(2, "0");
  const nextDate = String(nextDay.getDate()).padStart(2, "0");
  return `${nextYear}${nextMonth}${nextDate}`;
}

function createGoogleCalendarUrl(title, dateString, url, summary) {
  const startDate = formatDateForCalendar(dateString);
  const endDate = getNextDayFormatted(startDate);

  const eventTitle = encodeURIComponent(title || "Tech Event");
  const eventDetails = encodeURIComponent(`${summary || ""}\n\nEvent Link: ${url || ""}`);
  const datesParam = `${startDate}/${endDate}`;

  return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${eventTitle}&dates=${datesParam}&details=${eventDetails}`;
}

function addToGoogleCalendar(title, dateString, url, summary) {
  const calendarUrl = createGoogleCalendarUrl(title, dateString, url, summary);
  window.open(calendarUrl, "_blank", "noopener,noreferrer");
}
