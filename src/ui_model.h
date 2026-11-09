#pragma once
// Presentation-neutral view model for the text-producing flows.
//
// PlayFlow/CareerFlow/GarageFeatures keep emitting their existing row strings
// (tests and review scripts assert on them). This header classifies those rows
// into typed UI elements so the renderer can lay out menus, tuning sliders,
// stat tables and status chips instead of printing every string verbatim.
// Pure C++: no platform headers, covered by tests/ui_model_checks.cpp.
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <string>
#include <string_view>
#include <vector>

namespace racer::ui {

enum class RowKind {
  Option,  // selectable command (label)
  Slider,  // selectable "Label 1.00x [0.80-1.20] - hint": bar + value
  Field,   // selectable "Label: value" or "Label  value": label + value column
  Info,    // unselectable detail, key/value or sentence
  Warning, // UNSAVED / INVALID / Malformed / saving disabled
  Notice,  // DRAFT NOT APPLIED / Last action / NO ENGINE (amber)
  Spacer
};

enum class Icon { None, Check, Cross, Retry, Play, Stopwatch, Cog, Brush, Flag, Home, Power, Back, Car, Sliders, Plus, Minus, Layers, Pin, Bolt, Brake, Wheel };

struct Row {
  RowKind kind = RowKind::Info;
  std::string label, value, hint;
  bool selected = false;
  bool indented = false; // detail line belonging to the preceding group
  bool adjustable = false; // "[Left / Right]" cycles or adjusts the value
  Icon icon = Icon::None;
  std::vector<std::pair<std::string, std::string>> tiles; // "Time 8.0 s / Distance 111 m" -> stat tiles
  double current = 0, low = 0, high = 0; // Slider only
  int source = 0;                         // index into the original lines
};

struct KeyHint {
  std::string key, action;
};

struct Panel {
  std::string title, subtitle;
  std::vector<Row> rows;
  std::vector<KeyHint> hints;
  bool hasSelection = false;
};

inline bool contains(std::string_view s, std::string_view needle) {
  return s.find(needle) != std::string_view::npos;
}
inline bool isWarning(std::string_view s) {
  for (auto token : {"UNSAVED", "INVALID", "Malformed", "Saving disabled", "saving disabled"})
    if (contains(s, token)) return true;
  return false;
}
inline bool isNotice(std::string_view s) {
  return contains(s, "DRAFT NOT") || s.starts_with("Last action: ") || s.starts_with("NO ENGINE:");
}
inline bool isControlLine(std::string_view s) {
  return s.starts_with("Arrows / D-pad") || s.starts_with("ESC /") ||
         s.starts_with("WASD /") || s.starts_with("AUTOMATIC INPUT");
}
inline std::string trim(std::string_view s) {
  size_t a = 0, b = s.size();
  while (a < b && std::isspace(static_cast<unsigned char>(s[a]))) ++a;
  while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) --b;
  return std::string(s.substr(a, b - a));
}
inline std::string upper(std::string s) {
  for (auto& c : s) c = char(std::toupper(static_cast<unsigned char>(c)));
  return s;
}

// "GARAGE / Acura NSX '04" -> {"GARAGE", "Acura NSX '04"}.
inline void splitTitle(std::string_view line, std::string& title, std::string& subtitle) {
  const auto at = line.find(" / ");
  if (at == std::string_view::npos) {
    title = trim(line);
    subtitle.clear();
  } else {
    title = trim(line.substr(0, at));
    subtitle = trim(line.substr(at + 3));
  }
}

// Slider rows: "Acceleration 1.00x [0.80-1.20] - drive force".
inline bool parseSlider(std::string_view text, Row& out) {
  const auto open = text.find(" [");
  const auto x = text.rfind("x", open);
  if (open == std::string_view::npos || x == std::string_view::npos || x + 1 != open) return false;
  size_t numStart = x;
  while (numStart > 0 && (std::isdigit(static_cast<unsigned char>(text[numStart - 1])) || text[numStart - 1] == '.')) --numStart;
  if (numStart == x) return false;
  const auto close = text.find(']', open);
  const auto dash = text.find('-', open);
  if (close == std::string_view::npos || dash == std::string_view::npos || dash > close) return false;
  const std::string current(text.substr(numStart, x - numStart)),
      low(text.substr(open + 2, dash - open - 2)), high(text.substr(dash + 1, close - dash - 1));
  char* end = nullptr;
  const double c = std::strtod(current.c_str(), &end);
  if (end == current.c_str()) return false;
  const double l = std::strtod(low.c_str(), &end);
  if (end == low.c_str()) return false;
  const double h = std::strtod(high.c_str(), &end);
  if (end == high.c_str() || h <= l) return false;
  out.kind = RowKind::Slider;
  out.label = trim(text.substr(0, numStart));
  out.current = c;
  out.low = l;
  out.high = h;
  out.value = current + "x";
  const auto hint = text.find(" - ", close);
  if (hint != std::string_view::npos) out.hint = trim(text.substr(hint + 3));
  return true;
}

// "Label: value" -> field; a leading label of at most 32 bytes keeps prose out.
inline bool parseField(std::string_view text, Row& out) {
  const auto colon = text.find(": ");
  if (colon == std::string_view::npos || colon == 0 || colon > 32) return false;
  out.label = trim(text.substr(0, colon));
  out.value = trim(text.substr(colon + 2));
  return !out.value.empty();
}

// "Horizontal 0.00" / "Rotation 0.00 deg": word label then a trailing number (+ unit).
inline bool parseNumericTail(std::string_view text, Row& out) {
  const auto space = text.find(' ');
  if (space == std::string_view::npos || space == 0 || text.find(": ") != std::string_view::npos) return false;
  for (size_t i = 0; i + 1 < text.size(); ++i) {
    if (text[i] != ' ') continue;
    const auto tail = text.substr(i + 1);
    const char first = tail.front();
    if (!(std::isdigit(static_cast<unsigned char>(first)) || ((first == '-' || first == '+') && tail.size() > 1 && std::isdigit(static_cast<unsigned char>(tail[1]))))) continue;
    size_t end = 0;
    while (end < tail.size() && (std::isdigit(static_cast<unsigned char>(tail[end])) || tail[end] == '.' || (end == 0 && (tail[end] == '-' || tail[end] == '+')))) ++end;
    const auto unit = trim(tail.substr(end));
    if (unit.size() > 4 || !std::all_of(unit.begin(), unit.end(), [](unsigned char ch) { return std::isalpha(ch) != 0 || ch == '/' || ch == '%'; })) return false;
    out.label = trim(text.substr(0, i));
    out.value = std::string(tail.substr(0, end)) + (unit.empty() ? "" : (unit == "x" || unit == "%" ? unit : " " + unit));
    return true;
  }
  return false;
}

// Footer text -> keycap hints ("Arrows / D-pad: select, adjust | Enter / ...").
inline std::vector<KeyHint> parseHints(std::string_view line) {
  std::vector<KeyHint> out;
  size_t start = 0;
  while (start <= line.size()) {
    const auto bar = line.find(" | ", start);
    const auto part = line.substr(start, bar == std::string_view::npos ? line.npos : bar - start);
    const auto colon = part.find(": ");
    if (colon != std::string_view::npos) {
      auto keys = trim(part.substr(0, colon));
      const auto slash = keys.find(" / ");
      if (slash != std::string::npos) keys = keys.substr(0, slash);
      out.push_back({keys, trim(part.substr(colon + 2))});
    } else if (!trim(part).empty())
      out.push_back({"", trim(part)});
    if (bar == std::string_view::npos) break;
    start = bar + 3;
  }
  return out;
}

// Glyph for a menu entry, chosen from its wording (first match wins).
inline Icon iconFor(std::string_view label) {
  const std::string l = upper(std::string(label));
  struct Rule { const char* word; Icon icon; };
  static const Rule rules[] = {
      {"APPLY", Icon::Check}, {"SAVE", Icon::Check}, {"CANCEL", Icon::Cross}, {"DISCARD", Icon::Cross},
      {"REMOVE", Icon::Minus}, {"RESTORE", Icon::Retry}, {"RETRY", Icon::Retry}, {"QUIT", Icon::Power},
      {"RETURN", Icon::Back}, {"BACK", Icon::Back}, {"KEEP EDITING", Icon::Back}, {"FREE DRIVE", Icon::Wheel},
      {"DRIVE", Icon::Play}, {"RESUME", Icon::Play}, {"CONTINUE", Icon::Play}, {"START", Icon::Flag},
      {"TEST", Icon::Stopwatch}, {"AUTOMATIC", Icon::Stopwatch}, {"PLAYER RUN", Icon::Wheel}, {"PARTS", Icon::Cog},
      {"CATALOG", Icon::Cog}, {"OWNED", Icon::Cog}, {"INSTALL", Icon::Plus}, {"ACQUIRE", Icon::Plus}, {"ADD", Icon::Plus},
      {"BUY", Icon::Plus}, {"LIVERY", Icon::Brush}, {"DECAL", Icon::Brush}, {"LAYER", Icon::Layers}, {"EVENT", Icon::Flag},
      {"DESTINATION", Icon::Pin}, {"GARAGE", Icon::Home}, {"CAR", Icon::Car}, {"SETUP", Icon::Sliders},
      {"ACCELERATION", Icon::Bolt}, {"BRAKE", Icon::Brake}, {"STEERING", Icon::Wheel}};
  for (const auto& rule : rules)
    if (l.find(rule.word) != std::string::npos) return rule.icon;
  return Icon::None;
}

// "Accel 1.00x / Brake 1.00x" or "Time 8.000 s / Distance 111.2 m": 2-4 `Label number[unit]`
// segments become stat tiles. Anything else (prose, prices) is left alone.
inline std::vector<std::pair<std::string, std::string>> parseTiles(std::string_view text) {
  std::vector<std::pair<std::string, std::string>> out;
  size_t start = 0;
  while (start <= text.size()) {
    const auto bar = text.find(" / ", start);
    const auto part = trim(text.substr(start, bar == std::string_view::npos ? text.npos : bar - start));
    Row probe;
    if (!parseNumericTail(part, probe)) return {};
    out.emplace_back(probe.label, probe.value);
    if (bar == std::string_view::npos) break;
    start = bar + 3;
  }
  if (out.size() < 2 || out.size() > 4) return {};
  return out;
}

// optionCount: how many prefixed rows are real menu entries (PlayFlow::menuCount);
// further prefixed rows are detail lines that merely share the indent.
inline Panel parsePanel(const std::vector<std::string>& lines, size_t optionCount = size_t(-1)) {
  Panel out;
  size_t options = 0;
  if (lines.empty()) return out;
  splitTitle(lines.front(), out.title, out.subtitle);
  for (size_t i = 1; i < lines.size(); ++i) {
    std::string_view line = lines[i];
    if (line.empty()) {
      if (!out.rows.empty() && out.rows.back().kind != RowKind::Spacer) {
        Row spacer;
        spacer.kind = RowKind::Spacer;
        spacer.source = int(i);
        out.rows.push_back(spacer);
      }
      continue;
    }
    if (isControlLine(line)) {
      out.hints = parseHints(line);
      continue;
    }
    Row row;
    row.source = int(i);
    const bool selected = line.starts_with("> ");
    const bool prefixed = selected || (line.size() > 2 && line.starts_with("  ") && !std::isspace(static_cast<unsigned char>(line[2])));
    const bool menuRow = prefixed && options < optionCount;
    if (menuRow) ++options;
    std::string_view body = line;
    if (selected || line.starts_with("  ")) body = line.substr(2);
    row.selected = selected && menuRow;
    out.hasSelection |= row.selected;
    row.indented = prefixed && !menuRow;
    if (isWarning(line)) {
      row.kind = RowKind::Warning;
      row.label = trim(body);
    } else if (isNotice(line)) {
      row.kind = RowKind::Notice;
      row.label = trim(body);
    } else if (prefixed) {
      std::string text = trim(body);
      for (std::string_view adjust : {"[Left / Right]", "[Left/Right]"})
        if (text.size() >= adjust.size() && text.compare(text.size() - adjust.size(), adjust.size(), adjust) == 0) {
          row.adjustable = true;
          text = trim(std::string_view(text).substr(0, text.size() - adjust.size()));
          break;
        }
      row.label = text;
      if (parseSlider(text, row)) {
      } else if (parseField(text, row) || (menuRow && parseNumericTail(text, row))) {
        row.kind = RowKind::Field;
      } else
        row.kind = RowKind::Option;
      if (!menuRow) row.kind = row.kind == RowKind::Slider ? RowKind::Slider : RowKind::Info;
    } else {
      row.kind = RowKind::Info;
      row.label = trim(body);
      const bool groupHeader = i + 1 < lines.size() && lines[i + 1].starts_with("  ") && lines[i + 1].size() > 2 && lines[i + 1][2] != ' ';
      if (!groupHeader && body.find('[') == std::string_view::npos) row.tiles = parseTiles(body);
      Row probe;
      if (parseField(body, probe)) {
        row.label = probe.label;
        row.value = probe.value;
      }
    }
    if (row.kind == RowKind::Option || row.kind == RowKind::Slider || row.kind == RowKind::Field) row.icon = iconFor(row.label);
    out.rows.push_back(std::move(row));
  }
  while (!out.rows.empty() && out.rows.back().kind == RowKind::Spacer) out.rows.pop_back();
  return out;
}

// Selectable rows only, in order (what the arrow keys walk).
inline std::vector<size_t> selectable(const Panel& panel) {
  std::vector<size_t> out;
  for (size_t i = 0; i < panel.rows.size(); ++i) {
    const auto k = panel.rows[i].kind;
    if ((k == RowKind::Option || k == RowKind::Slider || k == RowKind::Field) && !panel.rows[i].indented) out.push_back(i);
  }
  return out;
}

inline double sliderFraction(const Row& row) {
  return row.high > row.low ? std::clamp((row.current - row.low) / (row.high - row.low), 0., 1.) : 0;
}

} // namespace racer::ui
