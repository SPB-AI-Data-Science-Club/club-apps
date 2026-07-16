# Curriculum content for the members portal.
#
# One entry per meeting day. This is the single source of truth that seeds the
# curriculum_days table on startup. Copy is written to read naturally for
# students, with no semicolons or em dashes.
#
# Fields:
#   day        meeting number (also the order shown)
#   title      the day's headline
#   hook       one or two flowing sentences that sell the day
#   topics     the concepts covered, shown as chips
#   activity   { title, desc, tool, url }  the in-class activity and its tool
#   game       built-in live game for the day, or None
#              one of: "quiz", "poll", "wager", "jeopardy"
#   game_set   which content set the live game loads (see game_content.py)
#
# Admins can override the activity link per day from the day page, so anything
# that needs a fresh Colab or Google Form each session can be pointed there
# without editing this file.

DAYS = [
    {
        "day": 1,
        "title": "Anatomy of a Model",
        "hook": "Every model starts as a simple shape trying to fit the world. Today you meet linear and "
                "logistic regression and learn how a loss function turns a guess into a score you can improve.",
        "topics": ["Linear regression", "Logistic regression", "Loss functions", "Fitting", "Residuals"],
        "activity": {
            "title": "Guess the Line",
            "desc": "In teams you drag a line through a cloud of points and try to make the squared error as "
                    "small as you can. The residuals are the gaps you are fighting. Lowest error on the "
                    "projector takes the round.",
            "tool": "Desmos",
            "url": "https://www.desmos.com/calculator",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 2,
        "title": "How Models Learn",
        "hook": "A model learns by taking small steps downhill. Today you follow gradient descent and see how "
                "one setting, the learning rate, decides whether it glides to the bottom or bounces off the walls.",
        "topics": ["Gradient descent", "Learning rate", "Convergence", "Overshooting", "Local minima"],
        "activity": {
            "title": "Gradient Descent Sandbox",
            "desc": "Each team hunts for the learning rate that reaches the minimum in the fewest steps. Set it "
                    "too high and the ball flies off the map, set it too low and it barely moves. Land in the "
                    "shallow valley and you have found a local minimum.",
            "tool": "Gradient Descent Lab",
            "url": "/labs/gradient",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 3,
        "title": "Overfitting and Regularization",
        "hook": "A model that memorizes the answers looks brilliant until it meets new data. Today you learn to "
                "spot that trap and use regularization to keep a model honest.",
        "topics": ["Overfitting vs underfitting", "Bias and variance", "L1 and L2 regularization",
                   "Model complexity"],
        "activity": {
            "title": "The Overfit Trap",
            "desc": "Teams pick a polynomial degree that aces the training points, then watch their curve crash "
                    "when the hidden test points appear live on the screen. The steady curve wins, not the fancy one.",
            "tool": "Overfit Lab",
            "url": "/labs/overfit",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 4,
        "title": "Evaluating Models",
        "hook": "Accuracy alone can lie to you. Today you build the vocabulary of honest evaluation, from the "
                "confusion matrix up through precision, recall, and the ROC curve.",
        "topics": ["Train and test split", "Cross validation", "Precision and recall", "F1 score", "ROC and AUC"],
        "activity": {
            "title": "Metrics Jeopardy",
            "desc": "A projected board with categories like Confusion Matrix, Precision vs Recall, and ROC. "
                    "Teams pick tiles, answer on their devices, and climb the live leaderboard.",
            "tool": "Live game",
            "url": "",
        },
        "game": "jeopardy",
        "game_set": "metrics",
    },
    {
        "day": 5,
        "title": "Decision Trees",
        "hook": "A decision tree asks the sharpest question it can, over and over, until it reaches an answer. "
                "Today you learn what makes a question sharp and how a tree measures its own confidence.",
        "topics": ["Tree splits", "Gini impurity", "Entropy", "Information gain", "Feature importance"],
        "activity": {
            "title": "Twenty Questions, Tree Edition",
            "desc": "The class guesses a mystery item using only the highest information gain questions it can "
                    "think of. Fewest questions wins, and then you race the same puzzle against Akinator to see "
                    "how a real tree plays.",
            "tool": "Akinator",
            "url": "https://en.akinator.com",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 6,
        "title": "Ensembles and Random Forests",
        "hook": "One tree can be fooled, but a whole forest rarely is. Today you learn why combining many "
                "shaky models produces one steady answer.",
        "topics": ["Bagging", "Random forests", "Variance reduction", "Wisdom of the crowd"],
        "activity": {
            "title": "Wisdom of the Crowd",
            "desc": "Everyone submits a guess for the count in the jar. The class average lands closer than "
                    "almost every single person, which is exactly why a forest beats one tree.",
            "tool": "Live game",
            "url": "",
        },
        "game": "poll",
        "game_set": "jar",
    },
    {
        "day": 7,
        "title": "Gradient Boosting",
        "hook": "Boosting builds a team of models where each one fixes the mistakes of the last. Today is Kaggle "
                "day, so you take that idea straight to a live leaderboard.",
        "topics": ["Boosting", "Fitting residuals", "XGBoost", "Early stopping"],
        "activity": {
            "title": "Boosting Showdown",
            "desc": "Teams add one tiny tree at a time and watch the leftover error, the residual, shrink with "
                    "every round. Race to pull the training error under the target line in the fewest trees, then "
                    "see whose ensemble also holds up on the test set instead of overfitting.",
            "tool": "Boosting Lab",
            "url": "/labs/boosting",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 8,
        "title": "Feature Engineering and Leakage",
        "hook": "The right feature can win a competition, and the wrong one can quietly ruin it. Today you learn "
                "to build strong features and to catch the leaks that make a model look better than it is.",
        "topics": ["Feature creation", "Encodings", "Scaling", "Target leakage", "Temporal leakage"],
        "activity": {
            "title": "The Leakage Heist",
            "desc": "A hidden leaky feature rockets every team to ninety nine percent, and then the true hold "
                    "out data is revealed and the scores collapse. Teams race to find the best honest feature instead.",
            "tool": "Leakage Lab",
            "url": "/labs/leakage",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 9,
        "title": "Clustering",
        "hook": "Sometimes there are no labels, just data that wants to be grouped. Today you learn how k-means "
                "and DBSCAN find structure that nobody told them was there.",
        "topics": ["Unsupervised learning", "K-means", "Choosing k", "Elbow method", "DBSCAN"],
        "activity": {
            "title": "Human K-Means",
            "desc": "Students become data points and walk to the nearest volunteer centroid. The centroids "
                    "re-center, everyone walks again, and the room settles into clusters exactly the way the "
                    "algorithm does.",
            "tool": "K-means visualizer",
            "url": "https://www.naftaliharris.com/blog/visualizing-k-means-clustering/",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 10,
        "title": "Dimensionality Reduction",
        "hook": "High dimensional data is impossible to picture until you flatten it well. Today you learn how "
                "PCA and t-SNE squeeze many features into a map you can actually read.",
        "topics": ["Curse of dimensionality", "PCA", "Principal components", "t-SNE"],
        "activity": {
            "title": "Find Your Twin",
            "desc": "A short survey turns everyone into a point in a high dimensional space, then the room is "
                    "projected onto a flat map. People react to who lands next to whom and why.",
            "tool": "PCA visualizer",
            "url": "https://setosa.io/ev/principal-component-analysis/",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 11,
        "title": "Neural Networks",
        "hook": "A neural network is a stack of simple units that together learn surprisingly rich patterns. "
                "Today you build one by hand and watch it bend to fit the data.",
        "topics": ["Perceptron", "Multilayer perceptron", "Weights and biases", "Activation functions",
                   "Forward pass"],
        "activity": {
            "title": "Playground Challenge",
            "desc": "Teams configure a network to untangle the spiral dataset. Fewest neurons and fastest "
                    "convergence wins, so every extra unit has to earn its place.",
            "tool": "TensorFlow Playground",
            "url": "https://playground.tensorflow.org",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 12,
        "title": "Backpropagation",
        "hook": "Backpropagation is how a network figures out which weights to blame for a mistake. Today you "
                "trace the chain rule through one update and then let the machine do thousands.",
        "topics": ["Loss gradients", "Chain rule", "Backpropagation", "Weight updates", "Epochs"],
        "activity": {
            "title": "One Update by Hand",
            "desc": "Teams step through a single backprop update with pencil and paper, then run the live network "
                    "and watch the loss curve fall epoch after epoch while the decision boundary bends into shape.",
            "tool": "Backprop Lab",
            "url": "/labs/backprop",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 13,
        "title": "Convolutional Neural Networks",
        "hook": "Images have structure that plain networks waste. Today you learn how convolutions and pooling "
                "let a model see edges, shapes, and eventually whole objects.",
        "topics": ["Convolution", "Filters and kernels", "Feature maps", "Pooling", "Why CNNs suit images"],
        "activity": {
            "title": "Fool the Classifier",
            "desc": "Groups train a quick image model in Teachable Machine, then compete to find inputs that "
                    "trick a rival team's model into confident nonsense.",
            "tool": "Teachable Machine",
            "url": "https://teachablemachine.withgoogle.com",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 14,
        "title": "Word Embeddings",
        "hook": "Words become math when you place them in space, and suddenly meaning has a direction. Today you "
                "explore vectors where king minus man plus woman really does point at queen.",
        "topics": ["Word vectors", "word2vec", "Cosine similarity", "Vector analogies"],
        "activity": {
            "title": "Analogy Race",
            "desc": "Teams roam the word cloud in the Embedding Projector, race to complete analogies, and hunt "
                    "for the funniest miss the vectors can produce.",
            "tool": "Embedding Projector",
            "url": "https://projector.tensorflow.org",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 15,
        "title": "Attention and Transformers",
        "hook": "Attention lets a model decide which words matter most to each other. Today you meet the "
                "architecture that powers nearly every modern language model.",
        "topics": ["Attention", "Query, key, value", "Self attention", "Transformer architecture"],
        "activity": {
            "title": "Predict the Attention",
            "desc": "Given an ambiguous sentence, teams predict which words will attend to which, then check "
                    "their guess against the live heatmap inside the Transformer Explainer.",
            "tool": "Transformer Explainer",
            "url": "https://poloclub.github.io/transformer-explainer/",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 16,
        "title": "How LLMs Work",
        "hook": "A language model is a very good guesser of the next token. Today you learn how tokenization, "
                "context, and temperature turn that one trick into fluent text.",
        "topics": ["Tokenization", "Next token prediction", "Context window", "Temperature", "Hallucinations"],
        "activity": {
            "title": "Beat the Model",
            "desc": "Game show style, teams wager points on the next token before it is revealed. The lowest "
                    "surprise wins the round. Warm up by pulling a sentence apart in the tokenizer first.",
            "tool": "OpenAI Tokenizer",
            "url": "https://platform.openai.com/tokenizer",
        },
        "game": "wager",
        "game_set": "next_token",
    },
    {
        "day": 17,
        "title": "Prompt Engineering",
        "hook": "The same model can be brilliant or useless depending on how you ask. Today you learn the moves "
                "that reliably get better answers and the ones that quietly break.",
        "topics": ["In-context learning", "Zero shot vs few shot", "Chain of thought", "Prompt failure modes"],
        "activity": {
            "title": "Prompt Off Bracket",
            "desc": "Head to head, teams craft prompts for a hidden task in a real model. Outputs are judged "
                    "blind on a rubric and the bracket narrows until one team is left standing.",
            "tool": "Prompting Guide",
            "url": "https://www.promptingguide.ai",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 18,
        "title": "Reinforcement Learning",
        "hook": "Some models learn by doing, collecting rewards and regrets along the way. Today you feel the "
                "tension every agent faces between trying something new and cashing in what works.",
        "topics": ["Agents", "States, actions, rewards", "Exploration vs exploitation", "Multi-armed bandits"],
        "activity": {
            "title": "Candy Bandits",
            "desc": "Three volunteers hand out candy at secret rates and the class spends a limited number of "
                    "pulls to find the best one. Afterward you see who explored well and who exploited too soon.",
            "tool": "ReinforceJS",
            "url": "https://cs.stanford.edu/people/karpathy/reinforcejs/",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 19,
        "title": "AI Ethics, Bias, and Fairness",
        "hook": "A model trained on unfair data will repeat that unfairness at scale. Today you learn to name "
                "the kinds of bias and to weigh the tradeoffs between competing definitions of fair.",
        "topics": ["Data bias", "Demographic parity", "Equalized odds", "Fairness tradeoffs"],
        "activity": {
            "title": "Model on Trial",
            "desc": "Given the stats of a biased hiring model, teams play the vendor, the regulator, and the "
                    "rejected applicant, then argue which fix should actually ship.",
            "tool": "Survival of the Best Fit",
            "url": "https://www.survivalofthebestfit.com/",
        },
        "game": None,
        "game_set": None,
    },
    {
        "day": 20,
        "title": "Interpretability and Explainability",
        "hook": "A model that cannot explain itself is hard to trust. Today you crack open a black box and "
                "close the semester with a full review.",
        "topics": ["Black box vs glass box", "Feature importance", "SHAP", "Saliency maps",
                   "Spurious correlations"],
        "activity": {
            "title": "Model Detective, then Review",
            "desc": "A model made a strange call and teams use SHAP or saliency maps to expose the spurious "
                    "feature behind it, the classic case where snow in the photo secretly meant wolf. Then the "
                    "semester closes with a full AI Jeopardy review.",
            "tool": "Live game",
            "url": "https://shap.readthedocs.io",
        },
        "game": "jeopardy",
        "game_set": "review",
    },
]

# A short review quiz for each day that does not already have a headline game.
# The id points at a quiz set in game_content.py. Days 4, 6, 16, and 20 already
# run their own game, so they are left out here.
REVIEW_BY_DAY = {
    1: "day1", 2: "day2", 3: "day3", 5: "day5", 7: "day7", 8: "day8",
    9: "day9", 10: "day10", 11: "day11", 12: "day12", 13: "day13",
    14: "day14", 15: "day15", 17: "day17", 18: "day18", 19: "day19",
}
