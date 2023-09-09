import jax.numpy as jnp
from jax import random
from itertools import product
import tensorflow as tf

class SETDataset:
    def __init__(self, key, accepted_trials, rejected_trials, train_batch_size,):
        """
        Initialize the SETDataset class.
        
        Parameters:
            key (random.PRNGKey): The initial random key.
            accepted_trials (int): The number of accepted trials.
            rejected_trials (int): The number of rejected trials.
            train_batch_size (int): The size of training batches
        """
        self.key = key
        self.accepted_trials = accepted_trials
        self.rejected_trials = rejected_trials
        self.train_batch_size = train_batch_size
        
        self.encoded_colors = self.generate_encoded_colors()
        self.SET_dict = self.create_data_dict()
        self.instantiate_SET_dict()
        self.SET_grokked = {'Accepted': [], 'Rejected': []}
        self.SET_corrupted = {'Accepted': [], 'Rejected': []}
        
        self.training_dict = self.create_data_dict()
        self.fill_data_dict(self.training_dict, self.accepted_trials, self.rejected_trials,)
        
        self.testing_dict = self.create_data_dict()
        self.fill_data_dict(self.testing_dict, 1, 1,)

    def generate_subkey(self,):
        """
        Generate a new subkey for random operations.
        
        Returns:
            random.PRNGKey: The new subkey.
        """
        key, subkey = random.split(self.key)
        self.key = key
        return subkey

    def generate_encoded_colors(self,):
        """
        Generate encoded color vectors for 'G', 'P', and 'R'.
        
        Returns:
            dict: A dictionary containing the color codes 'G', 'P', and 'R' and their associated random vectors.
        """
        encoded_colors = {}
        subkey = self.generate_subkey()
        for color, new_key in zip(['G', 'P', 'R'], random.split(subkey, 3)):
            encoded_colors[color] = random.normal(new_key, (100,))
        return encoded_colors

    def create_data_dict(self,):
        """
        Create a dictionary of all color combinations.
        
        Returns:
            dict: A dictionary with keys as color combinations (e.g. 'GGG', 'GRR', etc.) and values as empty lists.
        """
        all_combinations = product(['G', 'P', 'R'], repeat=3)
        training_dict = {"".join(comb): [] for comb in all_combinations}
        return training_dict

    def instantiate_SET_dict(self,):
        """
        Fills the SET_dict with the standard SET labels.
        """
        for SET_combination in self.SET_dict:
            unique_colors = len(set(list(SET_combination)))

            if unique_colors == 2:
                self.SET_dict[SET_combination] = (-1, "")
            else:
                self.SET_dict[SET_combination] = (1, "")

    def print_SET_dict(self,):
        """
        Print the contents of SET_dict with SET combinations in the first column,
        label in the second column, and status in the last column.
        """
        print("Contents SET_dict:")
        print("SET_combination | Label | Status")
        for SET, (label, status) in self.SET_dict.items():
            print(f"{SET} | {label} | {status}")
    
    def create_trial(self, SET_combination, unique_colors,):
        """
        Create a trial with random "ball" positions and associated colors.
        
        Parameters:
            SET_combination (str): A string containing a sequence of colors like 'GGP', 'RPG', etc.
            unique_colors (int): The number of unique colors in the combination.
            
        Returns:
            tuple: A tuple containing:
                - input_array (jnp.ndarray): JAX array of shape (50, 100) representing the trial.
                - output_array (jnp.ndarray): JAX array of shape (1), value is either -1 or 1 based on unique colors.
        """
        # Initialize a zero JAX array with shape (50, 100)
        input_array = jnp.zeros((50, 100))
        
        # Select random "ball" positions, ensuring minimum index distance of 5 between each "ball"
        while True:
            subkey = self.generate_subkey()
            ball_indices = sorted(random.randint(subkey, shape=(3,), minval=3, maxval=40))
            if all(ball_indices[i] - ball_indices[i-1] >= 5 for i in range(1, len(ball_indices))):
                break
                
        # Place the color vectors based on the random "ball" positions
        for i, ball_idx in enumerate(ball_indices):
            color = SET_combination[i]
            color_vector = self.encoded_colors[color]
            input_array = input_array.at[ball_idx].add(color_vector)
            input_array = input_array.at[ball_idx + 1].add(color_vector)
            
        # Determine the output_array based on the uniqueness of colors
        output_array = jnp.array([-1.0]) if unique_colors == 2 else jnp.array([1.0])
        
        return (input_array, output_array)

    def fill_data_dict(self, data_dict, accepted_trials, rejected_trials,):
        """
        Fill the data dictionary with trials based on unique colors.
        
        Parameters:
            data_dict (dict): The dictionary to be filled.
            accepted_trials (int): The number of accepted trials.
            rejected_trials (int): The number of rejected trials.
        """
        for SET_combination in data_dict:
            unique_colors = len(set(list(SET_combination)))

            if unique_colors == 2:
                for trial in range(rejected_trials):
                    data_dict[SET_combination].append(self.create_trial(SET_combination, unique_colors))

            else:
                for trial in range(accepted_trials):
                    data_dict[SET_combination].append(self.create_trial(SET_combination, unique_colors))

    def check_and_return_label(self, data_dict, SET_combination,):
        """
        Check if all labels for a given SET combination are the same and return that label.
        
        Parameters:
            data_dict (dict): The data dictionary containing trials.
            SET_combination (str): The SET combination to be checked.
            
        Returns:
            int: The label of the SET combination (-1 or 1).
        """
        SET_trials = data_dict[SET_combination]
        SET_labels = [trial[1].item() for trial in SET_trials]
        
        # Check if all labels are the same
        first_label = SET_labels[0]
        assert all(label == first_label for label in SET_labels), "Labels are not the same for all trials."
    
        return first_label

    def grok_specified_SET(self, SET,):
        """
        Remove specified SET from the training_dict.

        Parameters:
            SET (str): Specific SET to grok.
        """
        if SET in self.training_dict:
            unique_colors = len(set(list(SET)))
            if unique_colors == 2:
                self.SET_grokked['Rejected'].append(SET)
            else:
                self.SET_grokked['Accepted'].append(SET)

            self.SET_dict[SET] = (self.SET_dict[SET][0], 'Grokked')

            del self.training_dict[SET]

    def corrupt_specified_SET(self, SET,):
        """
        Inverse the label for specified SET from the training_dict and testing_dict.
    
        Parameters:
            SET (str): Specific SET to corrupt.
        """
        if SET in self.training_dict:
            unique_colors = len(set(list(SET)))
            if unique_colors == 2:
                self.SET_corrupted['Rejected'].append(SET)
            else:
                self.SET_corrupted['Accepted'].append(SET)
            
            self.SET_dict[SET] = (-self.SET_dict[SET][0], 'Corrupted')
    
            # Refill training data based on the new label
            num_trials = self.accepted_trials if unique_colors == 2 else self.rejected_trials
            new_trials = [self.create_trial(SET, unique_colors) for _ in range(num_trials)]
            self.training_dict[SET] = new_trials
    
            # Modify training and testing data
            self.training_dict[SET] = [(x[0], -x[1]) for x in self.training_dict[SET]]
            self.testing_dict[SET] = [(x[0], -x[1]) for x in self.testing_dict[SET]]

    def grok_SET(self, num_SETs,):
        """
        Remove randomly selected SETs from the training_dict if they are not corrupted.

        Parameters:
            num_SETs (int): The number of SETs to grok.
        """
        available_sets = [SET for SET, value in self.SET_dict.items() if value[1] == '']
        selected_indices = random.choice(self.generate_subkey(), jnp.arange(len(available_sets)), shape=(num_SETs,), replace=False)
        grokked_sets = [available_sets[i] for i in selected_indices]

        for SET in grokked_sets:
            self.grok_specified_SET(SET)
            
    def corrupt_SET(self, num_SETs,):
        """
        Inverse the label for randomly selected SETs from the training_dict and testing_dict
        if they are not grokked.
    
        Parameters:
            num_SETs (int): The number of SETs to corrupt.
        """
        available_sets = [SET for SET, value in self.SET_dict.items() if value[1] == '']
        selected_indices = random.choice(self.generate_subkey(), jnp.arange(len(available_sets)), shape=(num_SETs,), replace=False)
        corrupted_sets = [available_sets[i] for i in selected_indices]
    
        for SET in corrupted_sets:
            self.corrupt_specified_SET(SET)
    
    def print_data_dict(self, data_dict):
        """
        Print two grids. One grid has all the positive label SET_combinations, 
        and the other grid has all the negative label SET_combinations.
        Within each grid, the status ('Grokked' or 'Corrupted') of each SET is displayed.
    
        Parameters:
            data_dict (dict): The data dictionary containing trials.
        """
        print("Accepting Grid:")
        print("SET_combinations | Number of Trials | Status")
        for comb in data_dict:
            label = self.check_and_return_label(data_dict, comb)
            if label == 1:
                status = self.SET_dict.get(comb, ('', ''))[1]  # Fetching status from SET_dict
                print(f"{comb} | {len(data_dict[comb])} | {status}")
                    
        print("\nRejecting Grid:")
        print("SET_combinations | Number of Trials | Status")
        for comb in data_dict:
            label = self.check_and_return_label(data_dict, comb)
            if label == -1:
                status = self.SET_dict.get(comb, ('', ''))[1]  # Fetching status from SET_dict
                print(f"{comb} | {len(data_dict[comb])} | {status}")

    def print_training_testing(self,):
        """
        Print all relevant information pertaining to training and testing dicts.
        """
        print("\nTRAINING DATA\n")
        self.print_data_dict(self.training_dict)
        print("\n----------")
        print("\nTESTING DATA\n")
        self.print_data_dict(self.testing_dict)
    
    def generate_numpy_tensor(self, data_dict):
        """
        Create features and labels tensors for the tensorflow dataset.
        
        Parameters:
            data_dict (dict): The data dictionary containing trials.
        
        Returns:
            tuple: A tuple containing:
                - features_tensor (jnp.ndarray): A tensor containing all the feature arrays stacked along axis 0. 
                  Shape is (total_trials, 50, 100).
                - labels_tensor (jnp.ndarray): A tensor containing all the label arrays stacked along axis 0.
                  Shape is (total_trials, 5, 1).
        """
        # Initialize lists to hold feature and label arrays
        features_list = []
        labels_list = []
        
        # Iterate through each SET_combination in the data_dict
        for SET_combination, trials in data_dict.items():
            for input_array, output_array in trials:
                features_list.append(input_array)
                
                # Expand the label from shape (1) to (5, 1)
                expanded_label = jnp.tile(output_array, (5, 1))
                labels_list.append(expanded_label)
        
        # Stack the features and labels to create the final tensors
        features_tensor = jnp.stack(features_list, axis=0)
        labels_tensor = jnp.stack(labels_list, axis=0)
        
        return features_tensor, labels_tensor
    
    def generate_tf_dataset(self, data_dict, batch_size):
        """
        Create a TensorFlow Dataset object from the provided data_dict and batch size.
        
        This method first generates JAX tensors for the features and labels using the 
        `generate_numpy_tensor` method. These tensors are then converted into a TensorFlow 
        Dataset, which is shuffled and batched based on the provided batch size.
        
        Parameters:
            data_dict (dict): The data dictionary containing trials for each SET_combination.
            batch_size (int): The number of samples to include in each batch.
            
        Returns:
            tf.data.Dataset: A shuffled and batched TensorFlow Dataset object ready for training or evaluation.
        """
        features_tensor, labels_tensor = self.generate_numpy_tensor(data_dict)
        dataset = tf.data.Dataset.from_tensor_slices((features_tensor, labels_tensor))
        subkey = self.generate_subkey()
        dataset = dataset.shuffle(dataset.cardinality(), reshuffle_each_iteration=True, seed=subkey[0].item())
        dataset = dataset.batch(batch_size, drop_remainder=True)
        dataset = dataset.prefetch(2)

        return dataset

    def tf_datasets(self,):
        """
        Create both training and testing TensorFlow Datasets.
        """
        training_tf_dataset = self.generate_tf_dataset(self.training_dict, self.train_batch_size)
        test_batch_size = sum([len(trials) for _, trials in self.testing_dict.items()])
        testing_tf_dataset = self.generate_tf_dataset(self.testing_dict, test_batch_size)

        return training_tf_dataset, testing_tf_dataset
    
if __name__ == "__main__":
    pass