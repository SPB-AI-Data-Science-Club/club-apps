# Self-study lesson content for the Learn mode.
#
# Each lesson has short teaching blocks and a few application questions. The
# multiple choice questions come from game_content (the same reviewed bank), and
# these application questions add auto-graded number and multi-select items plus
# a short written reflection. Copy avoids semicolons and em dashes and keeps a
# light, casual tone for high schoolers.
#
# Question types used here:
#   number  { q, answer, tol, unit, explain }        auto-graded
#   multi   { q, options, correct:[i,...], explain }  auto-graded, select all
#   short   { q, sample, explain }                    written, self-checked

def T(h, p):
    return {"h": h, "p": p}

# Which MCQ set in game_content backs each day.
MCQ_SET = {d: f"day{d}" for d in range(1, 21)}
MCQ_SET[4] = "metrics_quiz"

LESSONS = {
    1: {"teach": [
            T("The shape of a model", "A model is a rule that turns inputs into a prediction. The simplest one is a "
              "straight line. Linear regression finds the line that best matches your data so you can predict a "
              "number, like a price or a temperature. Logistic regression bends that idea to predict a probability "
              "instead, which is how you answer yes or no questions like pass or fail."),
            T("Loss and residuals", "To improve a model you need to score how wrong it is. A residual is the gap "
              "between a prediction and the real value. The loss function rolls all those gaps into one number, "
              "usually by squaring them so big misses hurt more and cannot cancel out. Training just means nudging "
              "the model to make that loss as small as possible.")],
        "apply": [
            {"type": "number", "q": "A model predicts a house sells for 300 thousand, but it actually sells for 340 "
             "thousand. How far off was the prediction, in thousands?", "answer": 40, "tol": 0.5, "unit": "thousand",
             "explain": "The residual is the gap between actual and predicted, so 340 minus 300 is 40."},
            {"type": "short", "q": "In one sentence, what is the difference between what linear regression and "
             "logistic regression predict?",
             "sample": "Linear regression predicts a continuous number while logistic regression predicts the "
             "probability of a yes or no outcome.",
             "explain": "One outputs a number on a scale, the other outputs a probability between 0 and 1."}]},

    2: {"teach": [
            T("Learning by feel", "A model learns with gradient descent, which is like a hiker feeling their way "
              "downhill in thick fog. At each step it checks the slope of the loss under its feet and takes a step "
              "in the downhill direction. Do that enough times and it settles at the bottom, where the loss is low."),
            T("The learning rate", "The learning rate sets how big each step is. Too big and the hiker leaps clean "
              "over the valley and bounces around or flies off entirely. Too small and it shuffles forward so slowly "
              "it never arrives. There is also the risk of settling in a local minimum, a small dip that is low but "
              "not the lowest point anywhere.")],
        "apply": [
            {"type": "multi", "q": "Which of these can happen when the learning rate is too high? Select all that apply.",
             "options": ["It overshoots the minimum", "It can diverge and blow up", "It converges very slowly",
                         "It bounces around without settling"], "correct": [0, 1, 3],
             "explain": "Too high causes overshooting, bouncing, and divergence. Slow crawling is the too-low problem."},
            {"type": "short", "q": "Why might a model settle in a local minimum instead of the global one?",
             "sample": "Gradient descent only sees the slope right where it is, so it can roll into a nearby dip and "
             "stop, never knowing a deeper valley exists elsewhere.",
             "explain": "It follows local slope, so a nearby valley can trap it."}]},

    3: {"teach": [
            T("Two ways to fail", "A model can fail by being too simple or too complex. Underfitting is too simple, "
              "it misses the real pattern and does poorly even on training data. Overfitting is the opposite, the "
              "model memorizes the training data down to the noise and then falls apart on anything new."),
            T("Keeping it honest", "The bias variance tradeoff is the tug of war between those two. Regularization "
              "is the main tool for pulling a model back from overfitting by penalizing complexity. L1 and L2 "
              "regularization add a cost for large weights, and L1 can push some weights all the way to zero, which "
              "quietly removes useless features.")],
        "apply": [
            {"type": "number", "q": "A model scores 98 percent on training data and 61 percent on test data. What is "
             "the gap in percentage points that signals overfitting?", "answer": 37, "tol": 0.5, "unit": "points",
             "explain": "98 minus 61 is a 37 point gap, a classic overfitting warning sign."},
            {"type": "multi", "q": "Which of these help fight overfitting? Select all that apply.",
             "options": ["More regularization", "A simpler model", "Memorizing the training set", "More training data"],
             "correct": [0, 1, 3],
             "explain": "Regularization, simplicity, and more data all help. Memorizing is overfitting itself."}]},

    4: {"teach": [
            T("Accuracy can lie", "Accuracy is the share of predictions you got right, and on its own it can fool "
              "you. If 99 out of 100 emails are not spam, a model that always guesses not spam is 99 percent accurate "
              "and totally useless. You need sharper tools."),
            T("Precision, recall, and curves", "Precision asks, of everything you flagged positive, how much really "
              "was. Recall asks, of everything that truly was positive, how much you caught. The F1 score balances "
              "the two. The ROC curve and its AUC summarize how well the model ranks positives above negatives across "
              "every threshold. And you always measure on a held out test set, never the data you trained on.")],
        "apply": [
            {"type": "number", "q": "A test set has 90 true positives and 10 false negatives. What is the recall, as "
             "a decimal?", "answer": 0.9, "tol": 0.02, "unit": "",
             "explain": "Recall is TP over TP plus FN, so 90 over 100 is 0.9."},
            {"type": "number", "q": "Out of 80 items the model flagged positive, 60 were truly positive. What is the "
             "precision, as a decimal?", "answer": 0.75, "tol": 0.02, "unit": "",
             "explain": "Precision is TP over everything flagged positive, so 60 over 80 is 0.75."}]},

    5: {"teach": [
            T("Twenty questions, automated", "A decision tree predicts by asking a chain of sharp yes or no "
              "questions until it reaches an answer. The trick is picking the sharpest question at each step, the one "
              "that best separates the data into cleaner groups."),
            T("Measuring a good split", "Gini impurity and entropy both measure how mixed up a group of labels is. "
              "A split is good if it lowers that mess a lot, and that drop is called information gain. The tree greedily "
              "picks the highest information gain split every time. Afterward, feature importance tells you which "
              "features the tree leaned on the most.")],
        "apply": [
            {"type": "multi", "q": "Which of these does a decision tree use to choose a split? Select all that apply.",
             "options": ["Information gain", "Gini impurity", "Entropy", "Cosine similarity"], "correct": [0, 1, 2],
             "explain": "Gain, Gini, and entropy all judge splits. Cosine similarity is for comparing vectors."},
            {"type": "short", "q": "Why is a split that sorts the data into pure groups considered a good split?",
             "sample": "Pure groups mostly share the same label, so the tree can predict confidently and needs fewer "
             "further questions.",
             "explain": "Purity means less mixing, which means more information gained."}]},

    6: {"teach": [
            T("A crowd of trees", "One decision tree is easy to fool, but a whole forest is not. A random forest "
              "trains many trees, each on a random sample of the data and features, then lets them vote. Bagging is "
              "that recipe of training on random samples and combining the results."),
            T("Why crowds win", "The magic is variance reduction. Each tree makes different mistakes, and when they "
              "vote those mistakes tend to cancel out, leaving a steadier answer. This is the same wisdom of the crowd "
              "effect where the average of many independent guesses beats almost every single guesser.")],
        "apply": [
            {"type": "multi", "q": "Which of these are true of bagging? Select all that apply.",
             "options": ["Each model sees a random sample", "It reduces variance", "It requires removing the labels",
                         "It combines many models"], "correct": [0, 1, 3],
             "explain": "Bagging samples the data, combines models, and lowers variance. Labels stay put."},
            {"type": "short", "q": "In one sentence, why does a random forest usually beat a single tree?",
             "sample": "The trees make different errors that cancel out when they vote, so the forest is steadier and "
             "less likely to be fooled than any one tree.",
             "explain": "Independent errors average away, lowering variance."}]},

    7: {"teach": [
            T("A team that fixes mistakes", "Boosting builds a team of models in sequence, where each new one focuses "
              "only on what the team got wrong so far. Instead of voting all at once like a forest, the models are "
              "added one after another, each nudging the result closer."),
            T("Fitting the leftovers", "Concretely, each new tree is trained to predict the residuals, the leftover "
              "errors of the current ensemble. Add enough small trees and the error melts away. XGBoost is the famous "
              "library that does this and wins competitions. Early stopping halts training once the validation error "
              "stops improving, so you do not overfit.")],
        "apply": [
            {"type": "short", "q": "In boosting, what does each new tree try to predict?",
             "sample": "The residuals, meaning the leftover errors that the current ensemble still gets wrong.",
             "explain": "Boosting fits new models to the mistakes so far."},
            {"type": "multi", "q": "Which of these are true of gradient boosting? Select all that apply.",
             "options": ["Models are added in sequence", "Each one fixes the previous errors",
                         "All trees train independently at the same time", "Early stopping helps avoid overfitting"],
             "correct": [0, 1, 3],
             "explain": "Boosting is sequential and corrective. Training all at once independently is bagging."}]},

    8: {"teach": [
            T("Features make or break a model", "Feature engineering is the craft of turning raw data into inputs a "
              "model can use. That includes encoding categories into numbers, scaling features onto a common range, "
              "and building new columns that capture something useful."),
            T("The leak that flatters you", "The dangerous flip side is leakage, when a feature secretly contains the "
              "answer. Target leakage uses information you would never actually have at prediction time, and temporal "
              "leakage sneaks in data from the future. Both make a model look amazing in testing and then fail for "
              "real. If a brand new model scores 99 percent, get suspicious.")],
        "apply": [
            {"type": "multi", "q": "When predicting if a patient has a disease at intake, which features would leak "
             "the answer? Select all that apply.",
             "options": ["The diagnosis code entered later", "The treatment prescribed after diagnosis",
                         "Age at intake", "Blood pressure at intake"], "correct": [0, 1],
             "explain": "Anything recorded after the diagnosis leaks it. Intake values are fair game."},
            {"type": "short", "q": "Give one example of target leakage when predicting who will pass a class.",
             "sample": "Using the final exam score as a feature, since you would not have it before the final and it "
             "basically is the answer.",
             "explain": "A feature you only know after the outcome is leakage."}]},

    9: {"teach": [
            T("Finding groups with no labels", "Clustering is unsupervised learning, which means there are no labels "
              "to learn from. The model just looks for natural groups in the data. K-means is the classic method, "
              "where you pick a number of clusters and it settles points around moving centers called centroids."),
            T("How many groups", "Each round, every point joins its nearest centroid, then each centroid slides to "
              "the middle of its group, and you repeat until things stop moving. Choosing k, the number of clusters, "
              "is the tricky part, and the elbow method helps by showing where adding more clusters stops paying off. "
              "DBSCAN is an alternative that finds dense blobs and marks lonely points as outliers.")],
        "apply": [
            {"type": "number", "q": "You run k-means with k equal to 3. How many centroids will there be?",
             "answer": 3, "tol": 0, "unit": "centroids",
             "explain": "k is the number of clusters, and each cluster has exactly one centroid."},
            {"type": "short", "q": "How does the elbow method help you choose the number of clusters?",
             "sample": "You plot the error against k and look for the elbow where adding another cluster barely helps, "
             "which is a good balance point.",
             "explain": "The bend in the curve marks diminishing returns."}]},

    10: {"teach": [
            T("Too many dimensions", "When data has dozens or hundreds of features, it gets impossible to picture and "
              "harder to model. This is the curse of dimensionality. Dimensionality reduction squeezes the data down "
              "to a few meaningful directions while keeping most of the information."),
            T("PCA and t-SNE", "PCA finds the directions, called principal components, that capture the most variance "
              "in the data and keeps just those. t-SNE is a different tool built to flatten high dimensional data into "
              "a 2D map you can actually look at, so clusters and neighbors jump out. Fewer dimensions can also help "
              "fight overfitting.")],
        "apply": [
            {"type": "multi", "q": "Which of these are true of PCA? Select all that apply.",
             "options": ["It reduces the number of features", "It keeps directions of most variance",
                         "It requires labels", "It can help with overfitting"], "correct": [0, 1, 3],
             "explain": "PCA is unsupervised, so no labels needed. It trims features and keeps the high variance directions."},
            {"type": "short", "q": "Why is data with 50 features hard to visualize, and how does t-SNE help?",
             "sample": "We can only really see two or three dimensions at once, so 50 is impossible. t-SNE flattens it "
             "into a 2D map that keeps similar points close together.",
             "explain": "t-SNE makes a readable 2D picture of high dimensional data."}]},

    11: {"teach": [
            T("Neurons stacked in layers", "A neural network is built from tiny units called neurons, each one summing "
              "its inputs, adding a bias, and firing an output through an activation function. Stack them into hidden "
              "layers between the input and output and you get a network that can learn rich patterns."),
            T("Weights and the forward pass", "Every connection carries a weight, and those weights plus the biases are "
              "what the network learns. Running an input through the layers to get a prediction is the forward pass. "
              "The activation functions are essential, because without their nonlinearity a deep stack would collapse "
              "into one boring straight line.")],
        "apply": [
            {"type": "number", "q": "A dense layer has 4 inputs feeding into 3 neurons. Ignoring biases, how many "
             "weights connect them?", "answer": 12, "tol": 0, "unit": "weights",
             "explain": "Every input connects to every neuron, so 4 times 3 is 12 weights."},
            {"type": "short", "q": "Why do neural networks need nonlinear activation functions?",
             "sample": "Without them, stacking layers just gives another linear function, so the network could not "
             "learn curved or complex patterns.",
             "explain": "Nonlinearity is what lets deep networks model complex shapes."}]},

    12: {"teach": [
            T("Assigning blame", "Backpropagation is how a network figures out which weights caused its mistakes. After "
              "the forward pass produces a prediction and the loss measures how wrong it was, backprop sends that error "
              "backward through the network."),
            T("The chain rule at work", "It uses the chain rule from calculus to compute how much each weight "
              "contributed to the error, then nudges every weight a small step in the direction that lowers the loss. "
              "One full pass over the training data is an epoch, and repeating this for many epochs is what makes the "
              "loss curve slide down.")],
        "apply": [
            {"type": "multi", "q": "Which of these are true about training a network? Select all that apply.",
             "options": ["An epoch is one pass over the data", "Backprop uses the chain rule",
                         "Weights update to reduce loss", "A higher learning rate is always better"],
             "correct": [0, 1, 2],
             "explain": "The first three are core truths. A learning rate that is too high makes training diverge."},
            {"type": "short", "q": "In one sentence, what does backpropagation compute and what is it used for?",
             "sample": "It computes how much each weight contributed to the error, which is used to update the weights "
             "and lower the loss.",
             "explain": "Backprop finds the gradients that drive weight updates."}]},

    13: {"teach": [
            T("Networks that see", "Convolutional neural networks are built for images. Instead of connecting every "
              "pixel to every neuron, they slide small windows called filters or kernels across the image to detect "
              "little patterns like edges and corners."),
            T("From edges to objects", "Each filter produces a feature map showing where its pattern appears. Pooling "
              "layers then shrink those maps while keeping the strong signals, which saves work and adds robustness. "
              "Stack these and early layers find edges while deeper layers combine them into shapes and eventually "
              "whole objects. This works because nearby pixels in an image are usually related.")],
        "apply": [
            {"type": "multi", "q": "Which of these are parts of a CNN? Select all that apply.",
             "options": ["Convolution filters", "Pooling layers", "Feature maps", "Decision trees"],
             "correct": [0, 1, 2],
             "explain": "Filters, pooling, and feature maps are all CNN pieces. Trees belong to a different family."},
            {"type": "short", "q": "Why are convolutional layers a better fit for images than fully connected layers?",
             "sample": "They reuse small filters across the whole image and exploit the fact that nearby pixels are "
             "related, so they need far fewer weights and learn visual patterns better.",
             "explain": "Local filters match the structure of images and cut down parameters."}]},

    14: {"teach": [
            T("Words as math", "Word embeddings turn each word into a list of numbers, a vector, so a computer can do "
              "math with meaning. Methods like word2vec learn these vectors from the company a word keeps, meaning the "
              "words that tend to surround it."),
            T("Directions with meaning", "Once words are vectors, similar words sit close together and you can measure "
              "closeness with cosine similarity, which compares the angle between vectors. Even better, directions "
              "carry meaning, which is why king minus man plus woman lands right next to queen.")],
        "apply": [
            {"type": "multi", "q": "Which of these are true of word embeddings? Select all that apply.",
             "options": ["Words become vectors of numbers", "Similar words are close together",
                         "Cosine similarity compares them", "They store the dictionary definition"],
             "correct": [0, 1, 2],
             "explain": "Embeddings are learned vectors, not stored definitions. Similar words cluster and cosine "
             "similarity measures it."},
            {"type": "short", "q": "What does it mean that king minus man plus woman lands near queen?",
             "sample": "The direction from man to woman is the same gender direction that separates king from queen, so "
             "vector arithmetic captures the analogy.",
             "explain": "Consistent directions in the space encode relationships like gender or plural."}]},

    15: {"teach": [
            T("Deciding what matters", "Attention lets a model decide, for each word, which other words matter most to "
              "its meaning. In a sentence like the animal did not cross the street because it was tired, attention helps "
              "the model link it to animal rather than street."),
            T("Query, key, value", "Attention is computed from three vectors per word called the query, the key, and the "
              "value. Self attention applies this within a single sentence so every word can look at every other. The "
              "transformer architecture is built almost entirely on this idea, and it powers nearly every modern "
              "language model.")],
        "apply": [
            {"type": "multi", "q": "Which three vectors power attention? Select all that apply.",
             "options": ["Query", "Key", "Value", "Gradient"], "correct": [0, 1, 2],
             "explain": "Attention uses query, key, and value. Gradients belong to training, not attention itself."},
            {"type": "short", "q": "In your own words, what does attention let a model do?",
             "sample": "It lets each word focus on the other words that are most relevant to its meaning, instead of "
             "treating every word equally.",
             "explain": "Attention weighs relationships between words."}]},

    16: {"teach": [
            T("A very good next word guesser", "A large language model is, at heart, a machine that predicts the next "
              "token. Text is first chopped into tokens, small chunks that are often words or word pieces, and the "
              "model predicts what comes next, over and over, to produce fluent writing."),
            T("Context and temperature", "The context window is how much text the model can consider at once, its "
              "short term memory. Temperature controls how adventurous it is, with higher temperature giving more random "
              "and creative output and lower temperature staying safe and predictable. Because it is guessing, it can "
              "hallucinate, stating something false with complete confidence.")],
        "apply": [
            {"type": "multi", "q": "Which of these are true of large language models? Select all that apply.",
             "options": ["They predict the next token", "They can hallucinate", "The context window limits memory",
                         "They never make errors"], "correct": [0, 1, 2],
             "explain": "They predict tokens, can hallucinate, and are limited by the context window. They definitely "
             "make errors."},
            {"type": "short", "q": "Why does a higher temperature make a model more creative but also more error prone?",
             "sample": "Higher temperature makes it pick less likely tokens more often, which adds variety and surprise "
             "but also raises the chance of a wrong or odd choice.",
             "explain": "More randomness means more novelty and more mistakes."}]},

    17: {"teach": [
            T("Asking well", "The same model can be brilliant or useless depending on how you ask. In-context learning "
              "means the model can pick up a task just from what you put in the prompt. Zero-shot gives it no examples, "
              "while few-shot includes a handful to show the pattern."),
            T("Thinking out loud", "Chain of thought prompting asks the model to reason step by step before answering, "
              "which often improves hard problems. The most common way prompts fail is being vague, so being specific "
              "and giving examples usually helps a lot.")],
        "apply": [
            {"type": "multi", "q": "Which of these tend to improve a prompt? Select all that apply.",
             "options": ["Adding examples", "Asking for step by step reasoning", "Being specific", "Being vague"],
             "correct": [0, 1, 2],
             "explain": "Examples, reasoning, and specificity help. Vagueness is the classic failure mode."},
            {"type": "short", "q": "What is the difference between zero-shot and few-shot prompting?",
             "sample": "Zero-shot gives the model no examples and asks it to just do the task, while few-shot includes "
             "a few worked examples to show the pattern first.",
             "explain": "The difference is how many examples you put in the prompt."}]},

    18: {"teach": [
            T("Learning by doing", "Reinforcement learning trains an agent that acts in an environment. The agent sees "
              "a state, takes an action, and gets a reward, and its goal is to collect as much reward as possible over "
              "time by learning which actions pay off."),
            T("Explore or cash in", "The core tension is explore versus exploit. Exploring means trying something new to "
              "learn more, while exploiting means sticking with the best option you already know. Lean too far either "
              "way and you lose. The multi-armed bandit, like choosing which arcade machine to play, is the simplest "
              "version of this dilemma.")],
        "apply": [
            {"type": "multi", "q": "Which of these are parts of a reinforcement learning setup? Select all that apply.",
             "options": ["Agent", "States", "Actions", "Rewards"], "correct": [0, 1, 2, 3],
             "explain": "All four are core pieces of the reinforcement learning loop."},
            {"type": "short", "q": "Describe the explore versus exploit tradeoff in one sentence.",
             "sample": "You must balance trying new actions to discover better options against repeating the best action "
             "you already know to collect reward.",
             "explain": "It is the tension between gathering information and cashing in."}]},

    19: {"teach": [
            T("Bias in, bias out", "A model learns from data, so if that data reflects unfairness, the model will repeat "
              "it at scale. Bias can come from skewed samples, unbalanced groups, or human prejudice baked into the "
              "labels, and it often hides until someone checks."),
            T("Competing fairness ideas", "There are several mathematical definitions of fairness, like demographic "
              "parity, which asks for similar outcomes across groups, and equalized odds, which asks for similar error "
              "rates. The catch is that these definitions can genuinely conflict, so you often have to choose which one "
              "matters most for a given situation, and always ask who a model might harm.")],
        "apply": [
            {"type": "multi", "q": "Which of these can introduce bias into a model? Select all that apply.",
             "options": ["Biased training data", "Unbalanced groups", "Prejudice baked into the labels",
                         "Using a faster GPU"], "correct": [0, 1, 2],
             "explain": "Bias comes from the data and labels, not the hardware."},
            {"type": "short", "q": "Give one reason two fair-sounding fairness definitions might conflict.",
             "sample": "Demographic parity wants equal selection rates across groups while equalized odds wants equal "
             "error rates, and when the base rates differ you cannot satisfy both at once.",
             "explain": "Different fairness goals can be mathematically impossible to meet together."}]},

    20: {"teach": [
            T("Opening the black box", "A model you cannot see inside is a black box, and one you can explain is a glass "
              "box. Interpretability is about understanding why a model made a call, which matters for trust, debugging, "
              "and catching mistakes."),
            T("Tools and traps", "Feature importance shows which inputs the model leaned on most. SHAP values explain a "
              "single prediction by fairly splitting credit among the features, and saliency maps highlight which pixels "
              "of an image mattered. These tools can expose spurious correlations, like the famous model that told "
              "wolves from huskies mostly by spotting snow in the background rather than the animal itself.")],
        "apply": [
            {"type": "multi", "q": "Which of these are interpretability tools? Select all that apply.",
             "options": ["SHAP values", "Saliency maps", "Feature importance", "The loss function"],
             "correct": [0, 1, 2],
             "explain": "SHAP, saliency, and feature importance explain models. The loss function measures error."},
            {"type": "short", "q": "What is a spurious correlation, and why is the snow-equals-wolf example a problem?",
             "sample": "A spurious correlation is a pattern the model uses that is not actually the true cause. The model "
             "labeled wolves by the snow behind them, so it would fail on a wolf photographed on grass.",
             "explain": "The model latched onto the background, not the animal, so it will not generalize."}]},
}
