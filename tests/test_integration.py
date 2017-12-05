import unittest
import logging
from automl.pipeline import LocalExecutor, Pipeline, PipelineStep
from automl.data.dataset import Dataset
from automl.model import ModelSpace, Validate, CV, ChooseBest
from automl.feature.selector import FeatureSelector, VotingFeatureSelector_mult, VotingFeatureSelector_div
from automl.feature.generators import FormulaFeatureGenerator
from automl.hyperparam.hyperopt import Hyperopt
from automl.hyperparam.templates import random_forest_hp_space, knn_hp_space, svc_hp_space, grad_boosting_hp_space, xgboost_hp_space

from sklearn import datasets
from sklearn.datasets import make_classification, make_regression
from sklearn.linear_model import LogisticRegression, Lasso, Ridge
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier
from sklearn.kernel_ridge import KernelRidge
from sklearn.metrics import accuracy_score, mean_absolute_error, roc_auc_score, mean_squared_error

from xgboost.sklearn import XGBClassifier, XGBRegressor



class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)

    def test_step_validate(self):
        model_list = [
            (LogisticRegression, {}),
            (RandomForestClassifier, {'n_estimators': 100}),
            (GradientBoostingClassifier, {}),
            (SVC, {}),
            (KNeighborsClassifier, {}),
        ]

        data = Dataset(datasets.load_iris().data, datasets.load_iris().target)
        LocalExecutor(data) << (Pipeline() >>
            PipelineStep('model space', ModelSpace(model_list)) >>
            PipelineStep('validation', Validate(test_size=0.33, metrics=accuracy_score)) >>
            PipelineStep('choose', ChooseBest(3)))

    def test_step_cv(self):
        model_list = [
            (LogisticRegression, {}),
            (RandomForestClassifier, {'n_estimators': 100}),
            (GradientBoostingClassifier, {}),
            (SVC, {}),
            (KNeighborsClassifier, {}),
        ]

        data = Dataset(datasets.load_iris().data, datasets.load_iris().target)
        LocalExecutor(data) << (Pipeline() >> 
            PipelineStep('model space', ModelSpace(model_list)) >>
            PipelineStep('cv', CV('accuracy')) >>
            PipelineStep('choose', ChooseBest(3)))

    def test_step_space_regression_model(self):
        model_list = [
            (Lasso, {}),
            (Ridge, {}),
            (KernelRidge, {}),
        ]

        data = Dataset(datasets.load_boston().data, datasets.load_boston().target)
        LocalExecutor(data) << (Pipeline() >> 
            PipelineStep('model space', ModelSpace(model_list)) >>
            PipelineStep('cv', Validate(test_size=0.33, metrics=mean_absolute_error)) >>
            PipelineStep('choose', ChooseBest(3)))

    def test_all_step(self):
        model_list = [
            (Lasso, {}),
            (Ridge, {}),
            (KernelRidge, {}),
            (RandomForestRegressor, {})
        ]

        data = Dataset(datasets.load_boston().data, datasets.load_boston().target)
        context, pipeline_data = LocalExecutor(data, 10) << (Pipeline() >> 
            PipelineStep('model space', ModelSpace(model_list)) >>
            PipelineStep('feature generation', FormulaFeatureGenerator(['+', '-', '*'])) >>
            PipelineStep('cv', Validate(test_size=0.33, metrics=mean_squared_error)) >>
            PipelineStep('choose', ChooseBest(3)) >>
            PipelineStep('selection', FeatureSelector(30)))

        print('0'*30)
        for result in pipeline_data.return_val:
            print(result.model, result.score)
        print(pipeline_data.dataset.data.shape)
        print('0'*30)


    def test_pipeline_hyperopt(self):
        x, y = make_classification(
            n_samples=100,
            n_features=40,
            n_informative=2,
            n_redundant=10,
            flip_y=0.05)
        model_list = [
            (RandomForestClassifier, random_forest_hp_space()),
            #(GradientBoostingClassifier, grad_boosting_hp_space(lambda key: key)),
            #(SVC, svc_hp_space('name')),
            (KNeighborsClassifier, knn_hp_space(lambda key: key)),
            (XGBClassifier, xgboost_hp_space())
        ]

        data = Dataset(x, y)
        context, pipeline_data = LocalExecutor(data, 2) << (Pipeline() >> 
            PipelineStep('model space', ModelSpace(model_list), initializer=True) >>
            PipelineStep('feature generation', FormulaFeatureGenerator(['+', '-', '*'])) >>
            PipelineStep('H', Hyperopt(Validate(test_size=0.1, metrics=roc_auc_score), 
                                                max_evals=2)) >>
            PipelineStep('choose', ChooseBest(1)) 
            >> PipelineStep('selection', FeatureSelector(10))
            )

        print('0'*30)
        for result in pipeline_data.return_val:
            print(result.model, result.score)
        print(pipeline_data.dataset.data.shape)
        print('0'*30)

    def test_voting_feature_selector(self):
        """
        x, y = make_classification(
            n_samples=100,
            n_features=40,
            n_informative=2,
            n_redundant=10,
            flip_y=0.05
        )

        model_list = [
            (RandomForestClassifier, {}),
            (GradientBoostingClassifier, {}),
            (SVC, {}),
            (KNeighborsClassifier, {}),
            (XGBClassifier, {})
        ]
        """
        x, y = make_regression(
            n_samples=100,
            n_features=40,
            n_informative=2,
        )

        model_list = [
            (RandomForestRegressor, {}),
            (GradientBoostingRegressor, {}),
            (SVR, {}),
            (XGBRegressor, {})
        ]

        data = Dataset(x, y)

        result_mult = []
        result_div = []
        for i in range(100):
            context, pipeline_data = LocalExecutor(data, 10) << (Pipeline()
                >> PipelineStep('model space', ModelSpace(model_list), initializer=True)
                >> FormulaFeatureGenerator(['+', '-', '*', '/'])
                >> Validate(test_size=0.1, metrics=mean_absolute_error)
                >> ChooseBest(4)
                >> VotingFeatureSelector_mult(feature_to_select=10)
            )
            result_mult.append((pipeline_data.return_val[3].model, pipeline_data.return_val[3].score))

            context, pipeline_data = LocalExecutor(data, 10) << (Pipeline()
                >> PipelineStep('model space', ModelSpace(model_list), initializer=True)
                >> FormulaFeatureGenerator(['+', '-', '*', '/'])
                >> Validate(test_size=0.1, metrics=mean_absolute_error)
                >> ChooseBest(4)
                >> VotingFeatureSelector_div(feature_to_select=10)
            )
            result_div.append((pipeline_data.return_val[3].model, pipeline_data.return_val[3].score))

        result_compare = [(result_mult[i][1] > result_div[i][1], result_mult[i][0], result_div[i][0]) for i in range(0, 100)]

        errors = len([1 for i, j in zip(result_mult, result_div) if i[1]<j[1]])
        print('0'*30)
        for result in pipeline_data.return_val:
            print(result.model, result.score)
        print(pipeline_data.dataset.data.shape)
        print('0'*30)
        raise ValueError