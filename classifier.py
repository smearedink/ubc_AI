import random
import numpy as np
from sklearn.decomposition import RandomizedPCA as PCA
    

class combinedAI(object):
    """
    A class to combine different AIs, and have them operate as one
    """
    def __init__(self, list_of_AIs, strategy='vote', nvote=None):
        """
        inputs
        list_of_AIs: list of classifiers
        strategy: one of ['union', 'vote']
        
        Note: if nvote=None, we determine best nvote value during self.fit              

        """
        self.list_of_AIs = list_of_AIs
        self.strategy = strategy
        m = len(list_of_AIs)
        self.nvote = nvote

    def fit(self, pfds, target, **kwds):
        """
        args: [list of pfd instances], target
        """
        train_preds = []
        for clf in self.list_of_AIs:
            clf.fit(pfds,target, **kwds)

            if self.strategy == 'vote' and self.nvote == None:
                train_preds.append(clf.predict(pfds)) #nclassifiers x nsamples
                
# choose 'nvote' that maximizes the trianing-set performance                
        if self.strategy == 'vote' and self.nvote == None:
            train_preds = np.array(train_preds).transpose() #nsamples x nclassifiers
            score = 0.
            for i in range(len(self.list_of_AIs)):
                pct = (i+1.)/len(self.list_of_AIs)
                avepred = np.where(train_preds.sum(axis=1) > pct, 1, 0)
                this_score = np.mean(np.where(avepred == target, 1, 0))
                if this_score > score:
                    self.nvote = i + 1
                    score = this_score
                
                
    def predict(self, test_pfds, pred_mat=False ):
        """
        args: [list of test pfd instances], test target
        optionally: pred_mat = True returns the [nsamples x npredictions] matrix
                               so you can run your own prediction combo schemes
                               (default False)
        """
        if not type(test_pfds) in [list, np.ndarray]:
            print "warining: changing test_pfds from type %s to list" % (type(test_pfds))
            test_pfds = [test_pfds]
        self.list_of_predicts = []
        for clf in self.list_of_AIs:
            self.list_of_predicts.append(clf.predict(test_pfds))

        self.predictions = []
        for i in range(len(test_pfds)):
            if self.strategy == 'union':
                if any([c[i] for c in self.list_of_predicts]):
                    self.predictions.append(1)
                else:
                    self.predictions.append(0)
            elif self.strategy == 'vote':
                #predict = [c[i] for c in self.list_of_predicts]
                #if predict.count(1) > predict.count(0):
                    #self.predictions.append(1)
                #elif predict.count(1) == predict.count(0):
                    #if random.random() > 0.5:
                        #self.predictions.append(1)
                    #else:
                        #self.predictions.append(0)
                #else:
                    #self.predictions.append(0)
                predict = np.array(self.list_of_predicts)
                m,n = predict.shape
                #print m,n
                avepred = predict.sum(0)/m + np.array([(random.random()-0.5)*1.e-10 for i in range(n)])
                #print avepred.shape
                #print avepred
                self.predictions = np.where(avepred > np.ones(n)*self.nvote/float(m), 1, 0)

        #return np.array(self.predictions)
        if pred_mat:
            return predict #[nsamples x npredictions]
        else:
            return self.predictions

    def predict_proba(self, pfds):
        """
predict_proba(self, pfds) classifier method
    Compute the likehoods each possible outcomes of samples in T.
    
    The model need to have probability information computed at training
    time: fit with attribute `probability` set to True.
    
    Parameters
    ----------
    X : array-like, shape = [n_samples, n_features]
    
    Returns
    -------
    X : array-like, shape = [n_samples, n_classes]
        Returns the probability of the sample for each class in
        the model, where classes are ordered by arithmetical
        order.
    
    Notes
    -----
        """
        #for clf in self.list_of_AIs:
            #print clf.predict_proba(pfds)

        result = np.sum(np.array([clf.predict_proba(pfds) for clf in self.list_of_AIs]), axis=0)/len(self.list_of_AIs)
        return result
        



    def score(self, pfds, target, F1=True):
        """
        return the mean of success array [1,0,0,1,...,1], where 1 is being right, and 0 is being wrong.
        """
        predict = self.predict(pfds)
        if not F1:
            return np.mean(np.where(predict == target, 1, 0))
        else:
            P = np.mean(predict[target == 1])
            R = np.mean(target[predict == 1])
            F1score = 2 * P * R / (P + R)
            #print 'returnning F1:', F1
            #if F1 < 0.1:
                #print predict
                #print target
            return F1score



class classifier(object):
    """
    A class designed to be mixed in with the classifier class, to give it a feature property to specifiy what feature to extract.
    Usage:
    class svmclf(classifier, svm.SVC):
        orig_class = svm.SVC
        pass
    When initialize the classifier, remember to specify the feature like this:
    clf1 = svmclf(gamma=0.1, C=0.8, scale_C=False, feature={'phasebins':32})

    the feature has to be a diction like {'phasebins':32}, where 'phasebins' being the name of the feature, 32 is the size.
    """
    def __init__(self, feature=None, use_pca=False, n_comp=12, *args, **kwds):
        if feature == None:
            raise "must specifiy the feature used by this classifier!"
        self.feature = feature
        self.use_pca = use_pca
        self.n_components = n_comp
        super(classifier, self).__init__( *args, **kwds)

    def fit(self, pfds, target):
        """
        args: pfds, target
        pfds: the training pfds
        target: the training targets
        """
        #if 'train_pfds' in self.__dict__ and np.array(self.train_pfds == pfds).all() and str(self.feature) == self.last_feature:
            #print 'in fit, skipping extract'
            #data = self.train_data
        #else:
            #print 'in fit, not skipping extract'
            #data = np.array([pfd.getdata(**self.feature) for pfd in pfds])
            #self.train_pfds = tuple(pfds)
            #self.train_data = data
            #self.last_feature = str(self.feature)
        data = np.array([pfd.getdata(**self.feature) for pfd in pfds])
        current_class = self.__class__
        self.__class__ = self.orig_class
        if self.use_pca:
            self.pca = PCA(n_components=self.n_components).fit(data)
            data = self.pca.transform(data)
        results = self.fit( data, target)
        self.__class__ = current_class
        return results
        #return self.orig_class.fit(self, data, target)

    def predict(self, pfds):
        """
        args: pfds, target
        pfds: the testing pfds
        """
        #if 'test_pfds' in self.__dict__ and np.array(self.test_pfds == pfds).all() and str(self.feature) == self.last_feature:
            #print 'in predict, skipping extract'
            #data = self.test_data
        #else:
            #print 'in predict, not skipping extract'
            #data = np.array([pfd.getdata(**self.feature) for pfd in pfds])
            #self.test_pfds = tuple(pfds)
            #self.test_data = data
            #self.last_feature = str(self.feature)
        data = np.array([pfd.getdata(**self.feature) for pfd in pfds])
        #self.test_data = data
        current_class = self.__class__
        self.__class__ = self.orig_class
        if self.use_pca:
            data = self.pca.transform(data)
        results =  self.predict(data)
        self.__class__ = current_class
        return results
        #return self.orig_class.predict(self, data)
        
    def predict_proba(self, pfds):
        """
predict_proba(self, pfds) classifier method
    Compute the likehoods each possible outcomes of samples in T.
    
    The model need to have probability information computed at training
    time: fit with attribute `probability` set to True.
    
    Parameters
    ----------
    X : array-like, shape = [n_samples, n_features]
    
    Returns
    -------
    X : array-like, shape = [n_samples, n_classes]
        Returns the probability of the sample for each class in
        the model, where classes are ordered by arithmetical
        order.
    
    Notes
    -----
        """
        data = np.array([pfd.getdata(**self.feature) for pfd in pfds])
        current_class = self.__class__
        self.__class__ = self.orig_class
        if self.use_pca:
            data = self.pca.transform(data)
        results =  self.predict_proba(data)
        self.__class__ = current_class
        return results[...,1]

    def score(self, pfds, target, F1=True):
        """
        args: pfds, target
        pfds: the testing pfds
        target: the testing targets
        """
        #if 'test_pfds' in self.__dict__ and np.array(self.test_pfds == pfds).all() and str(self.feature) == self.last_feature:
            #print 'in score, skipping extract'
            #data = self.data
        #else:
            #print 'in score, not skipping extract'
            #data = np.array([pfd.getdata(**self.feature) for pfd in pfds])
            #self.test_pfds = tuple(pfds)
            #self.data = data
            #self.last_feature = str(self.feature)
        data = np.array([pfd.getdata(**self.feature) for pfd in pfds])
        current_class = self.__class__
        self.__class__ = self.orig_class
        if self.use_pca:
            data = self.pca.transform(data)
        #results =  self.score(data, target)
        predict = self.predict(data)
        if not F1:
            F1score = np.mean(np.where(predict == target, 1, 0))
        else:
            P = np.mean(predict[target == 1])
            R = np.mean(target[predict == 1])
            F1score = 2 * P * R / (P + R)
            #print 'returnning F1:', F1
            #if F1 < 0.1:
                #print predict
                #print target
        self.__class__ = current_class
        return F1score
        #return super(classifier, self).score(data, target)
        #return self.orig_class.score(self, data, target)

from sklearn import svm, linear_model
class svmclf(classifier, svm.SVC):
    """
    the mix-in class for svm.SVC
    """
    orig_class = svm.SVC
    pass

class LRclf(classifier, linear_model.LogisticRegression):
    """
    the mix-in class for svm.SVC
    """
    orig_class = linear_model.LogisticRegression
    pass


from ubc_AI import pulsar_nnetwork as pnn 
class pnnclf(classifier, pnn.NeuralNetwork):
    """ 
    the mixed in class for pnn.NeuralNetwork
    """
    orig_class = pnn.NeuralNetwork
    pass

from sklearn.tree import DecisionTreeClassifier
class dtreeclf(classifier, DecisionTreeClassifier):
    """ 
    the mixed in class for DecisionTree
    """
    orig_class = DecisionTreeClassifier
    pass
