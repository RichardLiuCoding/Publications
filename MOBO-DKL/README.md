# MOBO-DKL
Here is a collection of codes and data for the publication of **Autonomous Physics Discovery via Reward-Guided Multi-Objective Deep Learning in Ferroelectrics**.

To simplify the installation and environment setup process, We have provided all the codes and data in the format of standalone Google Colab notebooks. These notebooks contains all the codes and experimental data necessary to reproduce all the results and plots in the paper.

There are four notebooks in this folder:

* **MOBO_DKL_RL_dev_simulation**: this notebooks follows the same format and functionality of the one used in our real MOBO-DKL experiment. We simulated the effect of three different types of atomic impurities on the superconducting differential conductance spectra. We have selected three measured properties as rewards: superconducting gap size, gap symmetry, and in-gap states. The MOBO-DKL algorithm is applied to learn the Pareto front between these three rewards and train a model to predict the distribution of these properties based on topography map without access to the full spectroscopy map. It takes ~40 min to run on CPU, and ~10 min on T4 GPU in Colab.

* **MOBO_DKL_RL_dev_experimental_data**: this notebook is modified from the real one used in our MOBO-DKL experiment to visualize all the experimental results presented in the paper. Instead of making real-time decisions and acquire information from real instrument, this notebook loads the intermediate experimental data saved in our real MOBO-DKL experiments. 

* **Figure_plots**: this notebook is designed to generate all the plots and movies in the figure.

* **Jupiter_MOBO_DKL_Domain_botorch_v6**: this notebooks is the one that we used in real MOBO-DKL experiments. It's meant for visualization and exhibition instead of for running in Colab. Our intention for posting this notebook is that the readers can modify the **exp.measure()** and **exp.reward_mobo()** functions to deploy MOBO-DKL on their own instrument for active learning experiments. 
