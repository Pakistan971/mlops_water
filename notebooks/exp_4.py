import matplotlib.pyplot as plt
import seaborn as sns
import mlflow
from mlflow.models import infer_signature
from sklearn.model_selection import RandomizedSearchCV
import mlflow.sklearn
import dagshub
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score


mlflow.set_tracking_uri("https://dagshub.com/Pakistan971/mlops_water.mlflow")
dagshub.init(repo_owner='Pakistan971', repo_name='mlops_water', mlflow=True)
mlflow.set_experiment("Experiment4")

data = pd.read_csv(r"C:\Users\Shahbaz\mlops_new\water_potability.csv")
train_data, test_data = train_test_split(data,test_size=0.2,random_state=69)

def fill_missing_with_mean(df):
    for column in df.columns:
        if df[column].isnull().any():
            median_value = df[column].mean()
            df[column].fillna(median_value,inplace=True)
    return df

train_processed_data = fill_missing_with_mean(train_data)
test_processed_data = fill_missing_with_mean(test_data)


X_train = train_processed_data.drop(columns=["Potability"],axis=1)
y_train = train_processed_data["Potability"]
X_test = test_processed_data.drop(columns=["Potability"],axis=1)
y_test = test_processed_data["Potability"]

rf = RandomForestClassifier(random_state=69)

param_dist = {
    'n_estimators':[100,200,300,400,1000],
    'max_depth':[None,4,5,6,10]
}

random_search = RandomizedSearchCV(
    estimator=rf,
    param_distributions=param_dist,
    n_iter=50,
    cv=5,
    n_jobs=-1,
    random_state=69
)

with mlflow.start_run(run_name="Randome Forest Tuning") as parent_run:

    random_search.fit(X_train,y_train)

    for i in range(len(random_search.cv_results_['params'])):
        with mlflow.start_run(run_name=f"Combination{i+1}",nested=True) as child_run:
            mlflow.log_params(random_search.cv_results_['params'][i])
            mlflow.log_metric("mean_test_score",random_search.cv_results_['mean_test_score'][i])


    print(f"Best Parameters found: {random_search.best_params_}")
    mlflow.log_params(random_search.best_params_)
    mlflow.log_params(random_search.best_params_)

    # Train the model using the best parameters identified by RandomizedSearchCV
    best_rf = random_search.best_estimator_
    best_rf.fit(X_train, y_train)

    # Save the trained model to a file for later use
    pickle.dump(best_rf, open("model.pkl", "wb"))

    # Prepare the test data by separating features and target variable
    X_test = test_processed_data.drop(columns=["Potability"], axis=1)  # Features
    y_test = test_processed_data["Potability"]  # Target variable

    # Load the saved model from the file
    model = pickle.load(open('model.pkl', "rb"))

    # Make predictions on the test set using the loaded model
    y_pred = model.predict(X_test)

    # Calculate and print performance metrics: accuracy, precision, recall, and F1-score
    acc = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    # Log performance metrics into MLflow for tracking
    mlflow.log_metric("accuracy", acc)
    mlflow.log_metric("precision", precision)
    mlflow.log_metric("recall", recall)
    mlflow.log_metric("f1 score", f1)

    # Log the training and testing data as inputs in MLflow
    train_df = mlflow.data.from_pandas(train_processed_data)
    test_df = mlflow.data.from_pandas(test_processed_data)
    
    mlflow.log_input(train_df, "train")  # Log training data
    mlflow.log_input(test_df, "test")  # Log test data

    # Log the current script file as an artifact in MLflow
    mlflow.log_artifact(__file__)

    # Infer the model signature using the test features and predictions
    sign = infer_signature(X_test, random_search.best_estimator_.predict(X_test))
    
    # Log the trained model in MLflow with its signature
    mlflow.sklearn.log_model(random_search.best_estimator_, "Best Model", signature=sign)

    # Print the calculated performance metrics to the console for review
    print("Accuracy: ", acc)
    print("Precision: ", precision)
    print("Recall: ", recall)
    print("F1-score: ", f1)