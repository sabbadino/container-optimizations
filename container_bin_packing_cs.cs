using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Google.OrTools.Sat;

public class Item
{
    public int id { get; set; }
    public int weight { get; set; }
    public int volume { get; set; }
    public int? group_id { get; set; }
}

public class ContainerSpec
{
    public int volume { get; set; }
    public int weight { get; set; }
}

public class InputData
{
    public ContainerSpec container { get; set; }
    public List<Item> items { get; set; }
}

class ContainerBinPacking
{
    static void Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.WriteLine("Usage: dotnet run <input_json_file>");
            return;
        }
        string inputFilename = args[0];
        string json = File.ReadAllText(inputFilename);
        var data = JsonSerializer.Deserialize<InputData>(json);

        int containerVolume = data.container.volume;
        int containerWeight = data.container.weight;
        int numItems = data.items.Count;
        var itemIds = new List<int>();
        var itemVolumes = new List<int>();
        var itemWeights = new List<int>();
        var itemGroupIds = new List<int?>();
        for (int i = 0; i < numItems; i++)
        {
            var item = data.items[i];
            itemIds.Add(item.id != 0 ? item.id : i + 1);
            itemVolumes.Add(item.volume);
            itemWeights.Add(item.weight);
            itemGroupIds.Add(item.group_id);
        }

        // Build group-to-items mapping
        var groupToItems = new Dictionary<int, List<int>>();
        for (int i = 0; i < numItems; i++)
        {
            if (itemGroupIds[i].HasValue)
            {
                int gid = itemGroupIds[i].Value;
                if (!groupToItems.ContainsKey(gid))
                    groupToItems[gid] = new List<int>();
                groupToItems[gid].Add(i);
            }
        }
        var groupIds = new List<int>(groupToItems.Keys);

        int maxContainers = numItems;
        CpModel model = new CpModel();

        // Variables
        var x = new Dictionary<(int, int), IntVar>();
        for (int i = 0; i < numItems; i++)
            for (int j = 0; j < maxContainers; j++)
                x[(i, j)] = model.NewBoolVar($"x_{i}_{j}");
        var y = new List<IntVar>();
        for (int j = 0; j < maxContainers; j++)
            y.Add(model.NewBoolVar($"y_{j}"));

        // Each item in exactly one container
        for (int i = 0; i < numItems; i++)
        {
            var vars = new List<IntVar>();
            for (int j = 0; j < maxContainers; j++)
                vars.Add(x[(i, j)]);
            model.Add(LinearExpr.Sum(vars) == 1);
        }

        // Container capacity constraints
        for (int j = 0; j < maxContainers; j++)
        {
            var volTerms = new List<LinearExpr>();
            var wtTerms = new List<LinearExpr>();
            for (int i = 0; i < numItems; i++)
            {
                volTerms.Add(itemVolumes[i] * x[(i, j)]);
                wtTerms.Add(itemWeights[i] * x[(i, j)]);
            }
            model.Add(LinearExpr.Sum(volTerms) <= containerVolume * y[j]);
            model.Add(LinearExpr.Sum(wtTerms) <= containerWeight * y[j]);
        }

        // Link y[j] to usage
        for (int j = 0; j < maxContainers; j++)
            for (int i = 0; i < numItems; i++)
                model.Add(x[(i, j)] <= y[j]);

        // Soft grouping: penalize splitting a group across multiple containers
        int groupPenaltyLambda = 1;
        var groupInJ = new Dictionary<(int, int), IntVar>();
        var groupInContainers = new Dictionary<int, IntVar>();
        foreach (var g in groupIds)
        {
            for (int j = 0; j < maxContainers; j++)
            {
                groupInJ[(g, j)] = model.NewBoolVar($"group_{g}_in_{j}");
                foreach (var i in groupToItems[g])
                    model.Add(x[(i, j)] <= groupInJ[(g, j)]);
            }
            var groupInJVars = new List<IntVar>();
            for (int j = 0; j < maxContainers; j++)
                groupInJVars.Add(groupInJ[(g, j)]);
            groupInContainers[g] = model.NewIntVar(1, maxContainers, $"group_{g}_num_containers");
            model.Add(groupInContainers[g] == LinearExpr.Sum(groupInJVars));
        }

        // Objective: minimize number of containers used + penalty for group splits
        LinearExpr groupSplitPenalty = LinearExpr.Sum(
            groupIds.ConvertAll(g => groupInContainers[g] - 1)
        );
        model.Minimize(LinearExpr.Sum(y) + groupPenaltyLambda * groupSplitPenalty);

        // Solve
        CpSolver solver = new CpSolver();
        CpSolverStatus status = solver.Solve(model);
        Console.WriteLine($"Solver status: {status}");
        if (status == CpSolverStatus.Optimal || status == CpSolverStatus.Feasible)
        {
            int minContainers = 0;
            for (int j = 0; j < maxContainers; j++)
                if (solver.Value(y[j]) == 1) minContainers++;
            Console.WriteLine($"\nMinimum containers used: {minContainers}");
            // Group splits
            var groupSplits = new Dictionary<int, long>();
            foreach (var g in groupIds)
                groupSplits[g] = solver.Value(groupInContainers[g]) - 1;
            long totalGroupSplits = 0;
            foreach (var v in groupSplits.Values) totalGroupSplits += v;
            Console.WriteLine($"Total group splits (penalized): {totalGroupSplits}");
            // Output per container
            var usedContainerIndices = new List<int>();
            for (int j = 0; j < maxContainers; j++)
                if (solver.Value(y[j]) == 1) usedContainerIndices.Add(j);
            var containerRebase = new Dictionary<int, int>();
            for (int idx = 0; idx < usedContainerIndices.Count; idx++)
                containerRebase[usedContainerIndices[idx]] = idx + 1;
            foreach (var oldJ in usedContainerIndices)
            {
                int newJ = containerRebase[oldJ];
                var itemsInContainer = new List<int>();
                for (int i = 0; i < numItems; i++)
                    if (solver.Value(x[(i, oldJ)]) == 1) itemsInContainer.Add(i);
                int totalWeight = 0, totalVolume = 0;
                foreach (var i in itemsInContainer)
                {
                    totalWeight += itemWeights[i];
                    totalVolume += itemVolumes[i];
                }
                double pctWeight = containerWeight > 0 ? 100.0 * totalWeight / containerWeight : 0;
                double pctVolume = containerVolume > 0 ? 100.0 * totalVolume / containerVolume : 0;
                Console.WriteLine($"Container {newJ}: items [{string.Join(", ", itemsInContainer.ConvertAll(i => $"{itemIds[i]}(group_id={itemGroupIds[i]})"))}], total loaded weight: {totalWeight} ({pctWeight:F1}% of max), total loaded volume: {totalVolume} ({pctVolume:F1}% of max)");
            }
            // Group splits per group
            Console.WriteLine("\nGroup Splits:");
            Console.WriteLine("Group id | Containers used | Splits (penalized) | Container numbers");
            foreach (var g in groupIds)
            {
                var containersForGroup = new List<int>();
                foreach (var oldJ in usedContainerIndices)
                {
                    foreach (var i in groupToItems[g])
                    {
                        if (solver.Value(x[(i, oldJ)]) == 1)
                        {
                            containersForGroup.Add(containerRebase[oldJ]);
                            break;
                        }
                    }
                }
                string containersStr = string.Join(", ", containersForGroup);
                Console.WriteLine($"{g} | {solver.Value(groupInContainers[g])} | {groupSplits[g]} | {containersStr}");
            }
        }
        else
        {
            Console.WriteLine("No solution found.");
        }
    }
}
