#include "../includes/ResultsWriter.h"
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <algorithm>
#include <cctype>

namespace {

// JSON-escape a string (for keys and string values).
std::string jsonEscape(const std::string& s) {
	std::ostringstream out;
	for (char c : s) {
		if (c == '"') out << "\\\"";
		else if (c == '\\') out << "\\\\";
		else if (c == '\n') out << "\\n";
		else if (c == '\r') out << "\\r";
		else if (c == '\t') out << "\\t";
		else if (static_cast<unsigned char>(c) < 32)
			out << "\\u" << std::hex << std::setfill('0') << std::setw(4) << static_cast<unsigned>(static_cast<unsigned char>(c)) << std::dec;
		else
			out << c;
	}
	return out.str();
}

// Build day subpath: "M-D" (e.g. 3-11).
std::string monthDayPath() {
	using namespace std::chrono;
	auto now = system_clock::now();
	auto dp = floor<days>(now);
	year_month_day ymd(dp);
	unsigned m = static_cast<unsigned>(ymd.month());
	unsigned d = static_cast<unsigned>(ymd.day());
	std::ostringstream os;
	os << m << "-" << d;
	return os.str();
}

// Next exp index in day_dir (0 if no exp-* dirs exist).
int nextExpIndex(const std::string& dayDir) {
	namespace fs = std::filesystem;
	int next = 0;
	std::error_code ec;
	if (!fs::exists(dayDir, ec)) return 0;
	for (const auto& e : fs::directory_iterator(dayDir, ec)) {
		if (ec) continue;
		std::string name = e.path().filename().string();
		if (name.size() > 4 && name.compare(0, 4, "exp-") == 0) {
			std::string num = name.substr(4);
			if (std::all_of(num.begin(), num.end(), [](char c){ return std::isdigit(static_cast<unsigned char>(c)); })) {
				int n = std::stoi(num);
				if (n >= next) next = n + 1;
			}
		}
	}
	return next;
}

} // namespace

std::string writePlanResults(
	const std::string& inputYamlPath,
	const std::string& highLevelPlanner,
	const std::string& lowLevelPlanner,
	double maxPlanningTimeSec,
	int explanationCostBound,
	double explanationCostWeight,
	const Solution& solution,
	const std::vector<std::string>& agentNames,
	double planningTimeSec,
	size_t conflictsEvaluated,
	int sumOfCosts,
	int segmentCost)
{
	namespace fs = std::filesystem;

	std::string md = monthDayPath();
	std::string baseDir = "results/" + md;
	std::error_code ec;
	fs::create_directories(baseDir, ec);
	if (ec) {
		std::cerr << "Failed to create results base dir: " << baseDir << std::endl;
		return "";
	}

	int expN = nextExpIndex(baseDir);
	std::string expDir = baseDir + "/exp-" + std::to_string(expN);
	fs::create_directories(expDir, ec);
	if (ec) {
		std::cerr << "Failed to create experiment dir: " << expDir << std::endl;
		return "";
	}

	// Copy yaml to env.yaml
	std::string envYamlPath = expDir + "/env.yaml";
	fs::copy_file(inputYamlPath, envYamlPath, fs::copy_options::overwrite_existing, ec);
	if (ec) {
		std::cerr << "Failed to copy environment yaml to " << envYamlPath << std::endl;
		// continue to write JSON anyway
	}

	// Write result.json
	std::string jsonPath = expDir + "/result.json";
	std::ofstream out(jsonPath);
	if (!out) {
		std::cerr << "Failed to open " << jsonPath << " for writing." << std::endl;
		return "";
	}

	out << "{\n";
	// config
	out << "  \"config\": {\n";
	out << "    \"high_level_planner\": \"" << jsonEscape(highLevelPlanner) << "\",\n";
	out << "    \"low_level_planner\": \"" << jsonEscape(lowLevelPlanner) << "\",\n";
	out << "    \"max_planning_time_sec\": " << maxPlanningTimeSec << ",\n";
	out << "    \"explanation_cost_bound\": " << explanationCostBound << ",\n";
	out << "    \"explanation_cost_weight\": " << explanationCostWeight << "\n";
	out << "  },\n";

	// agents' plans (same structure as .txt: agent name -> list of states)
	out << "  \"plans\": {\n";
	for (size_t a = 0; a < solution.size(); ++a) {
		std::string name = (a < agentNames.size()) ? agentNames[a] : ("agent" + std::to_string(a));
		out << "    \"" << jsonEscape(name) << "\": [";
		const auto& path = solution[a];
		for (size_t i = 0; i < path.size(); ++i) {
			State* st = path[i];
			if (i) out << ", ";
			out << "{\"x\":" << st->x << ",\"y\":" << st->y << ",\"cost\":" << st->cost << "}";
		}
		out << "]";
		if (a + 1 < solution.size()) out << ",";
		out << "\n";
	}
	out << "  },\n";

	// metrics
	out << "  \"metrics\": {\n";
	out << "    \"planning_time_sec\": " << planningTimeSec << ",\n";
	out << "    \"conflicts_evaluated\": " << conflictsEvaluated << ",\n";
	out << "    \"sum_of_costs\": " << sumOfCosts << ",\n";
	out << "    \"segment_cost\": " << segmentCost << "\n";
	out << "  }\n";
	out << "}\n";

	out.close();
	std::cout << "Results written to: " << expDir << std::endl;

	// Auto-generate plot in the same results directory
	std::string plotPath = expDir + "/plot.png";
	std::string cmd = "python3 visualize.py " + expDir + " -o " + plotPath + " 2>/dev/null";
	int ret = std::system(cmd.c_str());
	if (ret != 0)
		std::cerr << "Warning: could not generate plot (ensure python3 with matplotlib and PyYAML is available)." << std::endl;
	else
		std::cout << "Plot saved to: " << plotPath << std::endl;

	return expDir;
}
