import logging
import unittest

import hyperopt

from automl.data.dataset import Dataset
from automl.hyperparam.templates import random_forest_hp_space, xgboost_hp_space
from automl.hyperparam.optimization import Hyperopt, HyperparameterSearchResult
from automl.model import CV, ModelSpace
from automl.pipeline import LocalExecutor, Pipeline
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier

from xgboost.sklearn import XGBClassifier


class TestHyperparameters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)

    def test_hyperopt(self):
        max_evals = 2
        x, y = make_classification()
        dataset = Dataset(x, y)
        result = LocalExecutor(dataset) << (
                                    Pipeline() 
                                    >> ModelSpace([(RandomForestClassifier, random_forest_hp_space())])
                                    >> Hyperopt(CV('roc_auc'), 
                                                max_evals=max_evals)
                                    )
        result = result[1].return_val[0]
        self.assertIsInstance(result.history, hyperopt.base.Trials) 
        self.assertEqual(len(result.history), max_evals) 

    def test_xgboost(self):
        max_evals = 2
        x, y = make_classification()
        dataset = Dataset(x, y)
        result = LocalExecutor(dataset) << (
                                    Pipeline() 
                                    >> ModelSpace([(XGBClassifier, xgboost_hp_space())])
                                    >> Hyperopt(CV('roc_auc'), 
                                                max_evals=max_evals)
                                    )
        result = result[1].return_val[0]
        self.assertIsInstance(result, HyperparameterSearchResult) 
        self.assertEqual(len(result.history), max_evals) 
