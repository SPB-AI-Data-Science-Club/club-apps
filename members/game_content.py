# Content library for the live game engine.
#
# Each set has a type that the engine knows how to run:
#   quiz   multiple choice, one right answer, points for being correct and fast
#   poll   everyone submits a number, the room sees the crowd against the truth
#   wager  teams bet points on the answer before it is revealed
#
# Jeopardy runs as its own projector game (see games/jeopardy.html) and is not
# part of this per-device engine, so it is not listed here.
#
# Shapes:
#   quiz:  { type, title, blurb, items:[ {q, options:[...], correct:int, seconds:int} ] }
#   poll:  { type, title, blurb, items:[ {q, answer:number, unit:str} ] }
#   wager: { type, title, blurb, start_score:int,
#            items:[ {q, options:[...], correct:int, note:str} ] }

CONTENT = {

    # ── QUIZ ───────────────────────────────────────────────────────────────
    "metrics_quiz": {
        "type": "quiz",
        "title": "Evaluating Models",
        "blurb": "A fast review of the metrics from Day 4.",
        "items": [
            {"q": "Of everything the model flagged as positive, the share that truly was positive is called what?",
             "options": ["Recall", "Precision", "Accuracy", "F1 score"], "correct": 1, "seconds": 20},
            {"q": "Of all the truly positive cases, the share the model actually caught is called what?",
             "options": ["Precision", "Specificity", "Recall", "AUC"], "correct": 2, "seconds": 20},
            {"q": "Which single score balances precision and recall as their harmonic mean?",
             "options": ["ROC", "Accuracy", "Log loss", "F1 score"], "correct": 3, "seconds": 20},
            {"q": "Data you hold back so you can measure performance on examples the model never trained on is the:",
             "options": ["Test set", "Training set", "Feature set", "Batch"], "correct": 0, "seconds": 20},
            {"q": "A model that predicts positive for everything gets high recall but poor:",
             "options": ["Recall", "Precision", "Bias", "Variance"], "correct": 1, "seconds": 20},
            {"q": "The area under the ROC curve mostly measures how well a model:",
             "options": ["Trains quickly", "Ranks positives above negatives", "Avoids overfitting", "Uses memory"],
             "correct": 1, "seconds": 25},
        ],
    },

    "foundations_quiz": {
        "type": "quiz",
        "title": "Foundations Review",
        "blurb": "A mixed review across the first half of the course.",
        "items": [
            {"q": "Training a model on data that already includes the correct answers is called:",
             "options": ["Unsupervised learning", "Supervised learning", "Reinforcement learning", "Clustering"],
             "correct": 1, "seconds": 20},
            {"q": "When a model memorizes the training data and fails on new data, it is:",
             "options": ["Underfitting", "Regularizing", "Overfitting", "Converging"], "correct": 2, "seconds": 20},
            {"q": "The setting that controls how big each gradient descent step is:",
             "options": ["Learning rate", "Epoch", "Batch size", "Loss"], "correct": 0, "seconds": 20},
            {"q": "Which method combines many decision trees to lower variance?",
             "options": ["Boosting", "Random forest", "PCA", "k-means"], "correct": 1, "seconds": 20},
            {"q": "The measure a decision tree uses to judge how mixed a group is:",
             "options": ["Gini impurity", "Cosine similarity", "Learning rate", "Recall"], "correct": 0,
             "seconds": 20},
            {"q": "k-means is an example of which kind of learning?",
             "options": ["Supervised", "Unsupervised", "Reinforcement", "Semi supervised"], "correct": 1,
             "seconds": 20},
        ],
    },

    "deep_quiz": {
        "type": "quiz",
        "title": "Neural Nets and Beyond",
        "blurb": "A review across the deep learning weeks.",
        "items": [
            {"q": "The algorithm that sends error backward through a network to update weights:",
             "options": ["Forward pass", "Backpropagation", "Pooling", "Tokenization"], "correct": 1,
             "seconds": 20},
            {"q": "Which layer type slides small filters across an image to find features?",
             "options": ["Dense", "Recurrent", "Convolutional", "Embedding"], "correct": 2, "seconds": 20},
            {"q": "In a transformer, attention is computed from three things called:",
             "options": ["Query, key, value", "Input, hidden, output", "Weight, bias, loss",
                         "Token, vector, score"], "correct": 0, "seconds": 25},
            {"q": "A language model fundamentally predicts the:",
             "options": ["Sentence length", "Next token", "Learning rate", "Loss curve"], "correct": 1,
             "seconds": 20},
            {"q": "Turning the word cat into a list of numbers produces a:",
             "options": ["Kernel", "Word vector", "Gradient", "Centroid"], "correct": 1, "seconds": 20},
            {"q": "Raising the temperature of a language model makes its output more:",
             "options": ["Predictable", "Random", "Accurate", "Compressed"], "correct": 1, "seconds": 20},
        ],
    },

    # ── POLL ───────────────────────────────────────────────────────────────
    "jar": {
        "type": "poll",
        "title": "Wisdom of the Crowd",
        "blurb": "Everyone guesses, then the crowd average takes on the truth.",
        "items": [
            {"q": "How many jellybeans are in the jar on the projector?", "answer": 412, "unit": "beans"},
            {"q": "How many words are on this slide?", "answer": 68, "unit": "words"},
            {"q": "How many paperclips are in the cup?", "answer": 137, "unit": "clips"},
        ],
    },

    # ── WAGER ──────────────────────────────────────────────────────────────
    "next_token": {
        "type": "wager",
        "title": "Beat the Model",
        "blurb": "Bet your points on the next token, then see if you beat the model.",
        "start_score": 1000,
        "items": [
            {"q": "The quick brown fox jumps over the lazy ___",
             "options": ["dog", "cat", "fence", "river"], "correct": 0,
             "note": "One of the most common sentences in text, so the model is very confident."},
            {"q": "To be or not to be, that is the ___",
             "options": ["answer", "question", "problem", "reason"], "correct": 1,
             "note": "A famous line the model has seen countless times."},
            {"q": "Water is made of hydrogen and ___",
             "options": ["carbon", "helium", "oxygen", "nitrogen"], "correct": 2,
             "note": "Facts that appear often are easy for the model to predict."},
            {"q": "I could not sleep, so I counted ___",
             "options": ["sheep", "stars", "money", "cards"], "correct": 0,
             "note": "A common idiom, though a few endings are plausible here."},
            {"q": "She opened the umbrella because it started to ___",
             "options": ["snow", "rain", "shine", "melt"], "correct": 1,
             "note": "Context makes one ending far more likely than the rest."},
        ],
    },
}


# ── Per-day review quizzes ──────────────────────────────────────────────────
# One short quiz per meeting so any day can close with a review game. The four
# headline-game days (4 Jeopardy, 6 poll, 16 wager, 20 Jeopardy) already have
# their own game, so they are not repeated here.
def _q(text, options, correct, seconds=20):
    return {"q": text, "options": options, "correct": correct, "seconds": seconds}

DAY_REVIEWS = {
    "day1": {"type": "quiz", "title": "Day 1 Review: Anatomy of a Model", "blurb": "Regression, loss, residuals.",
        "items": [
            _q("Linear regression predicts what kind of thing?",
               ["A yes or no", "A number", "A cluster", "A vibe"], 1),
            _q("The answer you need is yes or no. Which model do you grab?",
               ["Linear regression", "K-means", "Logistic regression", "A coin flip"], 2),
            _q("A residual is the gap between the prediction and what?",
               ["The average", "What actually happened", "The x axis", "Your expectations"], 1),
            _q("Training a model means making which number as small as possible?",
               ["The loss", "The dataset", "The slope", "Your screen time"], 0),
            _q("Why square the errors instead of just adding them up?",
               ["Squares look cooler", "So misses cannot cancel out and big misses hurt more",
                "It runs faster", "Nobody remembers"], 1),
        ]},
    "day2": {"type": "quiz", "title": "Day 2 Review: How Models Learn", "blurb": "Gradient descent and learning rate.",
        "items": [
            _q("Gradient descent is basically a hiker doing what?",
               ["Feeling their way downhill in fog", "Sprinting uphill", "Reading a trail map", "Waiting for rescue"], 0),
            _q("Learning rate way too high. What does the loss do?",
               ["Settles in gently", "Explodes past the minimum", "Drops straight to zero", "Nothing at all"], 1),
            _q("Learning rate way too low. What does training do?",
               ["Diverges", "Overfits", "Crawls along and basically stalls", "Skips the minimum"], 2),
            _q("Convergence means which thing finally stopped changing much?",
               ["The data", "The loss", "The learning rate", "The deadline"], 1),
            _q("A local minimum is a dip that is what?",
               ["Guaranteed to be the deepest", "Low, but maybe not the lowest anywhere", "Always at zero", "A rounding error"], 1),
        ]},
    "day3": {"type": "quiz", "title": "Day 3 Review: Overfitting", "blurb": "Bias, variance, regularization.",
        "items": [
            _q("A model aces the training data and bombs the test. Diagnosis?",
               ["Underfitting", "Convergence", "Overfitting", "Leakage"], 2),
            _q("Underfitting means the model is too what?",
               ["Fancy", "Simple", "Slow", "Confident"], 1),
            _q("Memorizing the answer key instead of learning the subject is which problem?",
               ["Overfitting", "Regularization", "Bagging", "Scaling"], 0),
            _q("Regularization keeps a model honest by punishing what?",
               ["Slow training", "Big datasets", "Complexity", "Wrong labels"], 2),
            _q("L1 regularization is famous for pushing some weights to what?",
               ["Infinity", "Exactly zero", "One", "Random values"], 1),
        ]},
    "day5": {"type": "quiz", "title": "Day 5 Review: Decision Trees", "blurb": "Splits, impurity, information gain.",
        "items": [
            _q("A decision tree reaches an answer by asking a chain of what?",
               ["Random guesses", "Sharp yes or no questions", "Neighbors", "Favors"], 1),
            _q("Gini impurity and entropy both measure how what a group is?",
               ["Large", "Mixed up", "Deep", "Expensive"], 1),
            _q("Information gain is how much a split reduces what?",
               ["Depth", "Speed", "Impurity", "Features"], 2),
            _q("At every node, the tree picks the split with the highest what?",
               ["Information gain", "Depth", "Cost", "Drama"], 0),
            _q("Feature importance tells you which features the tree did what with?",
               ["Loaded fastest", "Leaned on the most", "Deleted", "Invented"], 1),
        ]},
    "day7": {"type": "quiz", "title": "Day 7 Review: Gradient Boosting", "blurb": "Boosting and residuals.",
        "items": [
            _q("Boosting builds models in a sequence where each new one fixes what?",
               ["The dataset", "The previous one's mistakes", "The features", "The grading curve"], 1),
            _q("Each new boosted tree is usually trained to predict the last model's what?",
               ["Weights", "Inputs", "Residuals", "Homework"], 2),
            _q("XGBoost built its reputation winning what?",
               ["Image contests", "Tabular data competitions", "Chess", "Spelling bees"], 1),
            _q("Early stopping means you quit training when what stops improving?",
               ["Training error", "Validation error", "The vibe", "The learning rate"], 1),
            _q("A team of weak learners combined usually beats what?",
               ["Nothing", "One overconfident strong learner", "The test set", "Gravity"], 1),
        ]},
    "day8": {"type": "quiz", "title": "Day 8 Review: Features and Leakage", "blurb": "Encodings, scaling, leakage.",
        "items": [
            _q("One-hot encoding turns a category into what?",
               ["A single magic number", "Columns of zeros and ones", "A tree", "A longer string"], 1),
            _q("Scaling features puts them all on a common what?",
               ["Server", "Range", "Chart", "Grading scale"], 1),
            _q("Target leakage is when a feature secretly contains what?",
               ["Noise", "Duplicates", "The answer", "Typos"], 2),
            _q("Your brand new model instantly scores 99 percent. Correct reaction?",
               ["Celebrate", "Ship it", "Add more features", "Get suspicious"], 3),
            _q("Temporal leakage means training on information from the what?",
               ["Future", "Past", "Weekend", "Wrong class"], 0),
        ]},
    "day9": {"type": "quiz", "title": "Day 9 Review: Clustering", "blurb": "K-means, elbow, DBSCAN.",
        "items": [
            _q("Clustering works without labels, which makes it what kind of learning?",
               ["Supervised", "Unsupervised", "Reinforcement", "Optional"], 1),
            _q("K-means groups points around moving anchor points called what?",
               ["Leaves", "Kernels", "Centroids", "Team captains"], 2),
            _q("The elbow method helps you pick what?",
               ["The learning rate", "How many clusters to use", "The best feature", "A team name"], 1),
            _q("One k-means round: points join their nearest centroid, then each centroid does what?",
               ["Freezes", "Moves to the middle of its group", "Gets deleted", "Switches teams"], 1),
            _q("DBSCAN can flag lonely points that fit nowhere as what?",
               ["Centroids", "Winners", "New clusters", "Outliers"], 3),
        ]},
    "day10": {"type": "quiz", "title": "Day 10 Review: Dimensionality Reduction", "blurb": "PCA and t-SNE.",
        "items": [
            _q("The curse of dimensionality strikes when you have too many what?",
               ["Rows", "Features", "Models", "Group chats"], 1),
            _q("PCA compresses your features into a few new axes called what?",
               ["Clusters", "Tokens", "Principal components", "Mega features"], 2),
            _q("PCA keeps the directions holding the most what?",
               ["Variance", "Color", "Noise", "Rows"], 0),
            _q("t-SNE is mostly used to do what?",
               ["Train models faster", "Draw 2D maps of high dimensional data", "Delete features", "Label data"], 1),
            _q("Cutting down dimensions can also help fight which classic problem?",
               ["Underfitting", "Slow wifi", "Overfitting", "Missing labels"], 2),
        ]},
    "day11": {"type": "quiz", "title": "Day 11 Review: Neural Networks", "blurb": "Perceptrons, layers, activations.",
        "items": [
            _q("The tiny unit that sums its inputs and fires an output is a what?",
               ["Kernel", "Neuron", "Centroid", "Pixel"], 1),
            _q("The layers sitting between input and output are called what?",
               ["Shy layers", "Backup layers", "Hidden layers", "Middle layers"], 2),
            _q("The learnable numbers on the connections are the what?",
               ["Weights", "Tokens", "Labels", "Scores"], 0),
            _q("Strip out the activation functions and a deep network collapses into what?",
               ["A decision tree", "One boring linear function", "A cluster", "Pure chaos"], 1),
            _q("The forward pass computes the network's what?",
               ["Gradients", "Loss history", "Output", "Weights"], 2),
        ]},
    "day12": {"type": "quiz", "title": "Day 12 Review: Backpropagation", "blurb": "Chain rule and updates.",
        "items": [
            _q("Backpropagation sends what backward through the network?",
               ["The input", "Blame, in the form of gradients", "The labels", "The output"], 1),
            _q("Backprop runs on which rule from calculus?",
               ["The chain rule", "The product rule", "The power rule", "The honor rule"], 0),
            _q("Once the gradients are computed, the weights get what?",
               ["Deleted", "Frozen", "Nudged a small step against the gradient", "Doubled"], 2),
            _q("One full pass through all the training data is called an what?",
               ["Era", "Epoch", "Eon", "Attempt"], 1),
            _q("During healthy training, the loss curve mostly does what?",
               ["Rises", "Flatlines at the top", "Falls", "Vibrates randomly"], 2),
        ]},
    "day13": {"type": "quiz", "title": "Day 13 Review: CNNs", "blurb": "Convolution and pooling.",
        "items": [
            _q("Convolutional networks were built for which kind of data?",
               ["Spreadsheets", "Images", "Poems", "Playlists"], 1),
            _q("A convolution slides a small what across the image?",
               ["Window called a filter", "Ruler", "Cluster", "Caption"], 0),
            _q("The grid a filter produces as it scans the image is a what?",
               ["Residual", "Histogram", "Feature map", "Thumbnail"], 2),
            _q("Pooling does what to a feature map?",
               ["Enlarges it", "Shrinks it while keeping the strong signals", "Recolors it", "Deletes it"], 1),
            _q("CNNs make sense for photos because nearby pixels are usually what?",
               ["Unrelated", "Related", "Random", "Expensive"], 1),
        ]},
    "day14": {"type": "quiz", "title": "Day 14 Review: Word Embeddings", "blurb": "Vectors and analogies.",
        "items": [
            _q("A word embedding turns a word into a what?",
               ["Dictionary definition", "List of numbers", "Picture", "Tree"], 1),
            _q("word2vec figures out meaning from a word's what?",
               ["Spelling", "Length", "Surrounding words", "Font"], 2),
            _q("Cosine similarity compares two vectors using their what?",
               ["Length", "Angle", "Color", "Age"], 1),
            _q("king minus man plus woman lands closest to what?",
               ["Prince", "Throne", "Kingdom", "Queen"], 3),
            _q("Words with similar meanings end up where in the vector space?",
               ["Near each other", "Far apart", "At the origin", "On the axes"], 0),
        ]},
    "day15": {"type": "quiz", "title": "Day 15 Review: Attention", "blurb": "Attention and transformers.",
        "items": [
            _q("Attention lets each word decide which other words to what?",
               ["Ignore forever", "Focus on", "Delete", "Rhyme with"], 1),
            _q("The three vectors behind attention are query, key, and what?",
               ["Value", "Vault", "Verb", "Villain"], 0),
            _q("Self attention relates words inside the what?",
               ["Dictionary", "Same sentence", "Whole internet", "Weights file"], 1),
            _q("The transformer's headline move was building everything on what?",
               ["Convolution", "Recursion", "Attention", "Bigger GPUs"], 2),
            _q("Transformers are the backbone of modern what?",
               ["Databases", "Spreadsheets", "Firewalls", "Language models"], 3),
        ]},
    "day17": {"type": "quiz", "title": "Day 17 Review: Prompt Engineering", "blurb": "Prompting techniques.",
        "items": [
            _q("Showing the model worked examples inside your prompt is called what?",
               ["Fine tuning", "In-context learning", "Pretraining", "Bribery"], 1),
            _q("Zero-shot means your prompt includes how many examples?",
               ["Zero", "One", "A few", "All of them"], 0),
            _q("Chain-of-thought prompting asks the model to do what?",
               ["Answer faster", "Use fewer tokens", "Reason step by step before answering", "Cite its sources"], 2),
            _q("Few-shot prompting boosts quality by adding what?",
               ["More GPUs", "A handful of examples", "Capital letters", "Please and thank you"], 1),
            _q("The most common way a prompt fails is by being what?",
               ["Too specific", "Too vague", "Too long to read", "Too polite"], 1),
        ]},
    "day18": {"type": "quiz", "title": "Day 18 Review: Reinforcement Learning", "blurb": "Agents and rewards.",
        "items": [
            _q("In reinforcement learning, the learner is called the what?",
               ["Agent", "Player", "Student", "Bot"], 0),
            _q("The agent's whole goal is to rack up as much what as possible?",
               ["Loss", "Reward", "Steps", "Screen time"], 1),
            _q("Trying the mystery arcade machine instead of your usual is what?",
               ["Exploitation", "Convergence", "Exploration", "Regret"], 2),
            _q("Cashing in on the best option you already know is what?",
               ["Exploration", "Exploitation", "Overfitting", "Boosting"], 1),
            _q("The multi-armed bandit is a tiny model of which tradeoff?",
               ["Bias versus variance", "Speed versus accuracy", "Train versus test", "Explore versus exploit"], 3),
        ]},
    "day19": {"type": "quiz", "title": "Day 19 Review: Ethics and Fairness", "blurb": "Bias and fairness.",
        "items": [
            _q("Train a model on biased data and it will do what with the bias?",
               ["Quietly fix it", "Repeat it at scale", "Hide it forever", "Reverse it"], 1),
            _q("Most bias sneaks into a model through the what?",
               ["GPU", "Loss function", "Data", "Font"], 2),
            _q("Demographic parity asks for similar outcomes across what?",
               ["Time zones", "Groups of people", "Datasets", "Model versions"], 1),
            _q("Different mathematical definitions of fairness can do what?",
               ["Always agree", "Genuinely conflict with each other", "Be ignored safely", "Cancel each other out"], 1),
            _q("The first question before shipping a model should be who it might what?",
               ["Impress", "Entertain", "Confuse", "Harm"], 3),
        ]},
}
CONTENT.update(DAY_REVIEWS)

# Quizzes for the four headline-game days, so the self-study Learn mode has MCQs
# for every day. Day 4 reuses metrics_quiz, so only 6, 16, and 20 are added here.
CONTENT.update({
    "day6": {"type": "quiz", "title": "Day 6 Review: Ensembles", "blurb": "Bagging and random forests.",
        "items": [
            _q("A random forest is a big crowd of what, all voting together?",
               ["Neurons", "Decision trees", "Clusters", "Tokens"], 1),
            _q("Bagging trains each model on a slightly different what?",
               ["Computer", "Random sample of the data", "Loss function", "Color"], 1),
            _q("Combining many noisy models mainly reduces which thing?",
               ["Bias", "Variance", "Speed", "Data"], 1),
            _q("Why does a forest usually beat one tree?",
               ["It is bigger on disk", "Their mistakes cancel out", "Trees are trendy", "It uses the GPU"], 1),
            _q("Wisdom of the crowd works best when the voters are what?",
               ["Identical", "Independent and varied", "All experts", "All wrong"], 1),
        ]},
    "day16": {"type": "quiz", "title": "Day 16 Review: How LLMs Work", "blurb": "Tokens, context, temperature.",
        "items": [
            _q("Before a language model reads text, it chops it into what?",
               ["Pixels", "Tokens", "Clusters", "Frames"], 1),
            _q("At its core, a language model is just predicting the what?",
               ["Word count", "Next token", "Font", "Author"], 1),
            _q("The context window is basically how much the model can what?",
               ["Type", "Remember at once", "Download", "Draw"], 1),
            _q("Turning the temperature up makes the output more what?",
               ["Predictable", "Random and creative", "Accurate", "Compressed"], 1),
            _q("When a model states something false with total confidence, that is a what?",
               ["Bug report", "Hallucination", "Token", "Gradient"], 1),
        ]},
    "day20": {"type": "quiz", "title": "Day 20 Review: Interpretability", "blurb": "Explaining a model's choices.",
        "items": [
            _q("A model you cannot see inside is often called a what?",
               ["Glass box", "Black box", "Toolbox", "Sandbox"], 1),
            _q("Feature importance tells you which inputs the model did what with?",
               ["Deleted", "Leaned on most", "Ignored", "Encrypted"], 1),
            _q("SHAP values explain a prediction by splitting credit among the what?",
               ["Layers", "Features", "Epochs", "Students"], 1),
            _q("A saliency map for an image highlights which what mattered?",
               ["Colors", "Pixels", "Files", "Frames"], 1),
            _q("The wolf-versus-husky model really keyed on snow. That is a what?",
               ["Fair model", "Spurious correlation", "Good feature", "Random forest"], 1),
        ]},
})


# Which sets belong to each game type, for the admin console menus.
def sets_for(game_type):
    return [
        {"id": sid, "title": s["title"], "blurb": s.get("blurb", ""),
         "count": len(s.get("items", []))}
        for sid, s in CONTENT.items() if s["type"] == game_type
    ]


def get_set(set_id):
    return CONTENT.get(set_id)


# Jeopardy boards available to the projector game, surfaced in the console.
JEOPARDY_SETS = [
    {"id": "metrics", "title": "Model Metrics", "blurb": "Day 4 evaluation review."},
    {"id": "review", "title": "Semester Review", "blurb": "A wide Day 20 review board."},
    {"id": "ml_basics", "title": "Machine Learning Basics", "blurb": "Core supervised learning ideas."},
    {"id": "python", "title": "Python and Data Wrangling", "blurb": "Everyday data tools."},
]
