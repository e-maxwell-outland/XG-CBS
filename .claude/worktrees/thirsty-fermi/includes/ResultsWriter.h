#pragma once

#include "../includes/Environment.h"
#include <string>
#include <vector>
#include <filesystem>

// Shorthand for a plan (matches main.cpp)
typedef std::vector<std::vector<State*>> Solution;

// Writes a successful plan run to results/{M-D}/exp-{N}/:
//   - env.yaml (copy of input yaml)
//   - result.json (config, agents' plans, metrics)
// Returns the experiment directory path, or empty string on failure.
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
	int segmentCost
);
