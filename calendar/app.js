const translations = {
  en: {
    eyebrow: "/ CONTRIBUTIONS / LIVE HISTORY",
    title: "Contribution history",
    lede: "A compact, interactive view of public GitHub activity.",
    yearLabel: "YEAR",
    calendarSubtitle: "public activity · daily sync · contribution count by day",
    contribution: "contribution",
    contributions: "contributions",
    less: "LESS",
    more: "MORE",
    previous: "Previous year",
    next: "Next year",
    footer: "Use the year controls to move through every year with public activity.",
    backToProfile: "BACK TO PROFILE ↗",
    language: "Language",
    mon: "MON",
    wed: "WED",
    fri: "FRI",
  },
  es: {
    eyebrow: "/ CONTRIBUCIONES / HISTORIAL VIVO",
    title: "Historial de contribuciones",
    lede: "Una vista compacta e interactiva de la actividad pública en GitHub.",
    yearLabel: "AÑO",
    calendarSubtitle: "actividad pública · sincronización diaria · contribuciones por día",
    contribution: "contribución",
    contributions: "contribuciones",
    less: "MENOS",
    more: "MÁS",
    previous: "Año anterior",
    next: "Año siguiente",
    footer: "Usa los controles para recorrer cada año con actividad pública.",
    backToProfile: "VOLVER AL PERFIL ↗",
    language: "Idioma",
    mon: "LUN",
    wed: "MIÉ",
    fri: "VIE",
  },
};

const monthNames = {
  en: ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
  es: ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"],
};

const state = {
  language: "en",
  years: [],
  calendars: {},
  index: 0,
};

const $ = (selector) => document.querySelector(selector);

function currentCalendar() {
  return state.calendars[String(state.years[state.index])] || { weeks: [], months: [], totalContributions: 0 };
}

function currentYear() {
  return state.years[state.index];
}

function allDays(calendar) {
  return (calendar.weeks || []).flatMap((week) => week.contributionDays || []);
}

function activeDayCount(calendar) {
  return allDays(calendar).filter((day) => Number(day.contributionCount) > 0).length;
}

function updateText() {
  const t = translations[state.language];
  document.documentElement.lang = state.language;
  document.title = `xFrankB · ${t.title}`;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.dataset.i18n;
    if (t[key]) node.textContent = t[key];
  });
  $("#previousYear").setAttribute("aria-label", t.previous);
  $("#nextYear").setAttribute("aria-label", t.next);
  $(".language-switch").setAttribute("aria-label", t.language);
  $("#yearPicker").setAttribute("aria-label", t.yearLabel);
  document.querySelector('[data-weekday="1"]').textContent = t.mon;
  document.querySelector('[data-weekday="3"]').textContent = t.wed;
  document.querySelector('[data-weekday="5"]').textContent = t.fri;
}

function renderYearPicker() {
  const picker = $("#yearPicker");
  picker.replaceChildren();
  state.years.forEach((year, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = year;
    option.selected = index === state.index;
    picker.append(option);
  });
  $("#previousYear").disabled = state.index >= state.years.length - 1;
  $("#nextYear").disabled = state.index <= 0;
}

function renderMonths(calendar) {
  const monthRow = $("#monthRow");
  monthRow.replaceChildren();
  const weeks = calendar.weeks || [];
  monthRow.style.setProperty("--weeks", Math.max(weeks.length, 1));
  (calendar.months || []).forEach((month) => {
    const monthKey = String(month.firstDay || "").slice(0, 7);
    const start = weeks.findIndex((week) => String(week.firstDay || "").startsWith(monthKey));
    if (start < 0) return;
    const span = Math.max(Number(month.totalWeeks) || 1, 1);
    const label = document.createElement("span");
    label.className = "month-label";
    label.style.gridColumn = `${start + 1} / span ${span}`;
    const monthNumber = Number(monthKey.slice(5, 7)) - 1;
    label.textContent = monthNames[state.language][monthNumber] || month.name;
    monthRow.append(label);
  });
}

function dateText(date) {
  const parsed = new Date(`${date}T12:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return date;
  return new Intl.DateTimeFormat(state.language === "es" ? "es-MX" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

function renderGrid(calendar) {
  const grid = $("#calendarGrid");
  const weeks = calendar.weeks || [];
  const columns = Math.max(weeks.length, 1);
  grid.replaceChildren();
  grid.style.setProperty("--weeks", columns);
  grid.setAttribute("aria-label", `${translations[state.language].title} ${currentYear()}`);
  weeks.forEach((week, weekIndex) => {
    (week.contributionDays || []).forEach((day) => {
      const count = Number(day.contributionCount) || 0;
      const level = count ? String(day.contributionLevel || "FIRST_QUARTILE").toLowerCase().replaceAll("_", "-") : "none";
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = `day level-${level}${count ? " is-active" : ""}`;
      cell.style.gridColumn = String(weekIndex + 1);
      cell.style.gridRow = String(Number(day.weekday) + 1);
      const word = count === 1 ? translations[state.language].contribution : translations[state.language].contributions;
      cell.title = `${dateText(day.date)}: ${count} ${word}`;
      cell.setAttribute("aria-label", cell.title);
      cell.dataset.count = String(count);
      grid.append(cell);
    });
  });
}

function render() {
  const calendar = currentCalendar();
  const total = Number(calendar.totalContributions) || 0;
  const days = allDays(calendar).filter((day) => day.date).map((day) => day.date);
  updateText();
  renderYearPicker();
  renderMonths(calendar);
  renderGrid(calendar);
  $("#totalCount").textContent = total.toLocaleString(state.language === "es" ? "es-MX" : "en-US");
  $("#totalLabel").textContent = total === 1 ? translations[state.language].contribution : translations[state.language].contributions;
  $("#dateRange").textContent = days.length ? `${days[0]} → ${days[days.length - 1]}` : "—";
  document.body.dataset.activity = String(activeDayCount(calendar));
}

function setLanguage(language) {
  state.language = language;
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.classList.toggle("active", button.dataset.language === language);
  });
  render();
}

async function init() {
  const response = await fetch("./data.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`Unable to load contribution data: ${response.status}`);
  const data = await response.json();
  state.years = (data.years || []).map(Number).sort((a, b) => b - a);
  state.calendars = data.calendars || {};
  const current = Number(data.currentYear);
  state.index = Math.max(state.years.indexOf(current), 0);
  $("#yearPicker").addEventListener("change", (event) => {
    state.index = Number(event.target.value);
    render();
  });
  $("#previousYear").addEventListener("click", () => {
    if (state.index < state.years.length - 1) {
      state.index += 1;
      render();
    }
  });
  $("#nextYear").addEventListener("click", () => {
    if (state.index > 0) {
      state.index -= 1;
      render();
    }
  });
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.language));
  });
  render();
}

init().catch((error) => {
  console.error(error);
  $("#calendarGrid").innerHTML = `<p class="error">${error.message}</p>`;
});
