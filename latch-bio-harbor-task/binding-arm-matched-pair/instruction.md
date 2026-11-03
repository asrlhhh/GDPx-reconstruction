You have 6 hours of wall-clock time for this task. Your machine has 6 CPUs, 64 GiB of RAM and no GPU. When the time is up, you are stopped and your work is graded as it stands.

Your task is:
You are given the raw output of two independent binding assays run on twelve engineered variants of one antibody against a cell-surface receptor. Six of the twelve carry a single receptor-binding arm and six carry two. The delivered workbook holds the per-well reads from a concentration series on a receptor-expressing cell line, the complete per-cycle detector traces from the second assay, the manifest that ties each construct to its sample reference and its binding-arm format, and the conditions each assay was run under.

We will run a head-to-head in vivo comparison of one-arm versus two-arm receptor engagement. That comparison can isolate the effect of arm number only if the two constructs match on binding strength first, so that neither construct wins simply by binding harder.

Name the pair of constructs you would take forward into that comparison.

Report the construct identifiers exactly as they appear in the data.

Return EXACTLY:

{
  "matched_pair": ["<construct id>", "<construct id>"]
}

`matched_pair` carries exactly two construct identifiers.

IMPORTANT: When you have completed this task:
1. Write your final answer as a JSON object to a file named `analysis_output.json`
2. The file should contain ONLY the JSON object with the required fields
3. After writing the file, you have completed the task

Example analysis_output.json:
{
  "field1": value1,
  "field2": value2
}
You are working in a fixed environment that contains all data, packages, and tools needed to solve the task. Common biological analysis packages such as numpy, pandas, scipy, h5py, scanpy, and anndata have been pre-installed. Full build environment context can be found at `/root`, and all task data is present at `/workspace/data`. The environment has no internet access. Do not attempt to download data or packages, install or upgrade packages, or otherwise modify the environment. Solve the task using only the provided task instructions and data. Do not attempt to cheat or bypass the intended analysis. Biological data can be large, so be mindful of exhausting RAM and causing out-of-memory errors.

The calling program looks for results in `/workspace/analysis_output.json`. Hence, you should ensure to write a JSON object with the required fields before issuing the completion signal.

The completion signal is a standalone `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` command. You should always issue the completion signal after you have finished the task and submitted the final output.