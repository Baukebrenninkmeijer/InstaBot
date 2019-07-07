
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

users = io_method.read()  # Use whatever you want. Should be a dataframe when loaded.

clf = RandomForestClassifier()
df = users.loc[~(users.relation.isna())].drop(['scraped_from', 'username', 'biography', 'followed_at', 'unfollowed_at'], axis=1).fillna(0)
y = df['relation']
x = df.drop(['relation'], axis=1)
x_train, x_test, y_train, y_test = train_test_split(x, y)
clf.fit(x_train, y_train)
clf.score(x_test, y_test)