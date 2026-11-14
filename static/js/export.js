function downloadTextFile(content, fileName, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const downloadUrl = URL.createObjectURL(blob);
  const anchorElement = document.createElement("a");

  anchorElement.href = downloadUrl;
  anchorElement.download = fileName;
  document.body.appendChild(anchorElement);
  anchorElement.click();

  document.body.removeChild(anchorElement);
  URL.revokeObjectURL(downloadUrl);
}

function escapeCsvField(field) {
  if (field === null || field === undefined) {
    return '""';
  }
  const cleanField = String(field).replace(/"/g, '""');
  return `"${cleanField}"`;
}

function convertEventsToCsv(eventsList) {
  const headers = ["Title", "Date", "Priority", "Platform", "URL", "Summary"];
  const rows = eventsList.map((event) => {
    return [
      escapeCsvField(event.title),
      escapeCsvField(event.date),
      escapeCsvField(event.priority),
      escapeCsvField(event.platform || event.organizer),
      escapeCsvField(event.url),
      escapeCsvField(event.summary)
    ].join(",");
  });

  return [headers.join(","), ...rows].join("\n");
}

function convertEventsToMarkdown(eventsList, taskPrompt) {
  const titleHeader = `# Discovered Events Digest\n\n`;
  const promptHeader = taskPrompt ? `> **Search Query:** ${taskPrompt}\n\n` : "";
  const totalHeader = `**Total Events Found:** ${eventsList.length}\n\n---\n\n`;

  const eventEntries = eventsList.map((event, index) => {
    const title = event.title || "Untitled Event";
    const date = event.date || "TBD";
    const priority = event.priority || "MEDIUM";
    const platform = event.platform || event.organizer || "Web";
    const url = event.url || "#";
    const summary = event.summary ? `${event.summary}\n` : "";

    return `### ${index + 1}. [${title}](${url})\n- **Date:** ${date}\n- **Priority:** ${priority}\n- **Platform:** ${platform}\n${summary}\n`;
  });

  return `${titleHeader}${promptHeader}${totalHeader}${eventEntries.join("\n---\n\n")}`;
}

function exportEventsAsCsv(eventsList, taskId) {
  if (!eventsList || eventsList.length === 0) {
    alert("No events available to export.");
    return;
  }
  const csvContent = convertEventsToCsv(eventsList);
  const fileName = `events_task_${taskId || "export"}.csv`;
  downloadTextFile(csvContent, fileName, "text/csv;charset=utf-8;");
}

function exportEventsAsMarkdown(eventsList, taskId, taskPrompt) {
  if (!eventsList || eventsList.length === 0) {
    alert("No events available to export.");
    return;
  }
  const markdownContent = convertEventsToMarkdown(eventsList, taskPrompt);
  const fileName = `events_task_${taskId || "export"}.md`;
  downloadTextFile(markdownContent, fileName, "text/markdown;charset=utf-8;");
}
