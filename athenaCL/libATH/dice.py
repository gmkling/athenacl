#-----------------------------------------------------------------||||||||||||--
# Name:          dice.py
# Purpose:       dice models useful for making Voss-style noise.
#
# Authors:       Christopher Ariza
#
# Copyright:     (c) 2004 Christopher Ariza
# Note:          The implementation of GameNoise is based in part on an 
#                    implementation by Paul Berg.
# License:       GPL
#-----------------------------------------------------------------||||||||||||--



import random, math
from athenaCL.libATH import drawer
from athenaCL.libATH import unit
_MOD = 'dice.py'

#-----------------------------------------------------------------||||||||||||--
class Die:
    """definees a die object; can be continuous or have a number of sides
    if continuous, continuous values between 0 and 1 are possible
    if it has sides, the unit interval is divided by the number of sides; 
        the median of these-length segments are provided
    """
    def __init__(self, sideNo=0):
        self.sideNo = sideNo# zero sides is continueous
        self.sideBounds = []
        self.valueLast = None # last value rolled
        if self.sideNo != 0: # gets triplke of low, mean, max
            self.sideBounds = drawer.unitBoundaryEqual(self.sideNo)
        self.roll() # do an initial roll to set valueLast

    #-----------------------------------------------------------------------||--
    # public methods

    def roll(self):
        valCont = random.random() # continueous value
        if self.sideNo == 0:
            self.valueLast = valCont
        else: 
            i = drawer.unitBoundaryPos(valCont, self.sideBounds)
            a, m, b = self.sideBounds[i]
            self.valueLast = m

    def __call__(self):
        """call returns the last value rolled"""
        return self.valueLast

    def __str__(self):
        if self.sideNo == 0:
            sideStr = 'continuous'
        else:
            sideStr = '%s-sided' % str(self.sideNo)
        return sideStr



#-----------------------------------------------------------------||||||||||||--
class DiceUnit:
    def __init__(self, diceFmt):
        """multiple die objects, bundled together
        returned values are scaled by the number of dice, producing
            values within the unit interval
        diceFmt is a list of integers, each integer the number of 
            sides for the respective dice
        diceWeight are values that will scale dice values, corresponding
            to ordered positions; dice weights are floating point values
            that sum to one; non weighted dice equall to equal weights of 
            1 / number-of-dice
        """
        self.diceNo = len(diceFmt)
        self.dice = []
        for side in diceFmt: # append an object for each die
            self.dice.append(Die(side))
        # store last binArray used to determine to roll or not
        self.binArrayLast = [0] * self.diceNo
        # values of last roll, as a list
        self.valueLast = [] 
        self.valueWeight = []
        # store a default, even weight to save processing; list of equal values
        self.diceWeightDefault = [(1.0/self.diceNo)] * self.diceNo

    #-----------------------------------------------------------------------||--
    def roll(self, binArray, diceWeight=None):
        """provide a binary array to roll selected die in self.dice
        die is rolled only if value is not he same as previous"""
        # update the weight values if new values have been provided
        if diceWeight == None: # set to 1
            self.diceWeight = self.diceWeightDefault
        else:
            assert len(diceWeight) == self.diceNo
            self.diceWeight = diceWeight
        # roll dice, only if variance in change pattern
        for i in range(0, self.diceNo):
            if binArray[i] != self.binArrayLast[i]: # if 1
                self.dice[i].roll() 
        # rolls are measured and weighted now
        self.valueLast = [] # clear
        self.valueWeight = []
        for i in range(0, self.diceNo):
            valRaw = self.dice[i]() # values are between 0 and 1
            self.valueLast.append(valRaw) # call to report last values
            # scale by weight (weight sum must equal 1)
            valWeight = valRaw * self.diceWeight[i]
            self.valueWeight.append(valWeight)
        # store last bin array fro comparison
        self.binArrayLast = binArray

    def reset(self):
        """return to initial conditions"""
        self.binArrayLast = [0] * self.diceNo

    def __call__(self):              
        """report all values scaled over unit interval"""
        return self.valueWeight

    def sum(self):
        sum = 0
        for x in self.valueWeight:
            sum = sum + x
        return sum

    def __str__(self):
        msg = []
        for die in self.dice:
            msg.append(str(die))
        return 'dice %s' % ', '.join(msg)


#-----------------------------------------------------------------||||||||||||--
class GameNoise:
    def __init__(self, noVal):
        """1/f noise w/ dice simulation
        noVal is the resolution, number of values desired (not the number of dice)
        gamma is the noise index, usually between 0 and 4
            any gamma value is made negative
            0 white, 1 pink, 2 brown, 3, 4 black
        """
        self.noVal = noVal # desired number of values
        if self.noVal <= 0: raise ValueError, 'number of values must be greater than zerp'
        # find exponent that is greater than or equal to
        self.noDice = self._findNearestExp(self.noVal)
        # number of binary permutations must be an exp of 2 to be complete
        # create a list of game moves using binary arrays
        self.move = self._binarySeries(pow(2,self.noDice))
        self.movePos = 0 # current index
        self.moveLast = [] # store last completed move array
        # create a number of continuos dice; weight provided on roll
        diceFmt = [0] * self.noDice
        self.dice = DiceUnit(diceFmt)

        # temporaru init display
        #print _MOD, 'GameNoise:', 'noValues', self.noVal, 'noDice', self.noDice, 'noMoves', len(self.move)
        
    #-----------------------------------------------------------------------||--
    # methods for producing binary lists and proper exponents

    def _intToBinary(self, dec):
        if dec < 0: return None # bad value
        bin = []
        while dec: # until dec == 0
            if dec % 2: # prepends 1 or 0 if odd or even
                bin.append(1)
            else:
                bin.append(0)
            dec = long(dec/2)
        if bin == []: return [0]
        else: return bin
    
    def _findNearestExp(self, val):
        """find exponent such that pow(2,n) >= val"""
        exp = 0
        base = 2
        x = 0
        while x < val:
            exp = exp + 1
            x = pow(base, exp)
        return exp
    
    def _binarySeries(self, no):
        """produce a binary series as equal length lists
        if balance, round no to the nearest pow(2,n) values for n
        note: column of vals that change the least is on left
        """
        found = []
        for x in range(0, no):
            found.append(self._intToBinary(x))
        # max length will be last, 
        lenMax = len(found[-1])
        # fill values w/ zeros
        for i in range(0, len(found)):
            while len(found[i]) < lenMax:
                found[i] = found[i] + [0]
        # reverse direction of list; b/c weights are reversed
        for i in range(0, len(found)):
            found[i].reverse()
        return found    

    #-----------------------------------------------------------------------||--
    # methods for calculating the weight
    # note: weights have a minimum of 1, and max up to large numbers (65, 512)

    def _weightRawSingle(self, dieIndex, gamma):
        exp = (gamma + 1.0) * .5 * .6931472
        p = pow(math.e, -exp) # negative eponent
        return pow(p, dieIndex)

    def _updateGamma(self, gamma=None):
        """ make gamma <= 0; provide default if necessary"""
        if gamma == None: # provide default
            self.gamma = 0 # white noise
        else:
            self.gamma = gamma
        # make sure gamma is negative
        self.gamma = -abs(gamma)

    def _diceWeight(self, gamma=None):
        """get an array of dice weighting
        weights a proportion of sum for all weights;
        this proportion is used to scale the contribtion of each die
        to the final sum"""
        # updates self.gamma
        self._updateGamma(gamma)
        # calc raw weights, reverse, and normalize
        diceWeight = []
        for i in range(0, self.noDice): # dice index starts at 0
            diceWeight.append(self._weightRawSingle(i, self.gamma))
        # the higher the value of i, the less frequent the use of that weight
        # should be; if the left-most column of binary moves are the least 
        # common, then the highest value i should be on the left; thus reverse
        diceWeight.reverse()
        # normalize weights so sum == 1
        diceWeight = unit.unitNormProportion(diceWeight)
        return diceWeight


    #-----------------------------------------------------------------------||--
    def reset(self):
        self.movePos = 0
        self.dice.reset() # resets last move record

    def step(self, gamma):
        """play one move in the game
        dice weights are calculated for each step based only on the gamma value
        """
        # update gamma; default will cause no change
        # get this move, store for comparison
        self.moveLast = self.move[self.movePos]
        self.dice.roll(self.moveLast, self._diceWeight(gamma))

        # if move pos first, report gamma
        #if self.movePos == 0:
        #   print 'gamma', self.gamma, 'diceWeight', self.dice.diceWeight

        # incre position
        self.movePos = self.movePos + 1
        if self.movePos >= len(self.move):
            self.movePos = 0
        self.sumLast = self.dice.sum()


    def __call__(self):
        """returns the sum of the game
        this value is scaled w/n the unit interval"""
        return self.sumLast

    def __str__(self):
        # temporary representation
        sumStr = str(round(self.sumLast, 6)).ljust(8)
        sumScaleStr = str(int(round((self.sumLast*100), 0))).ljust(3)
        return '%s %s %s' % (self.moveLast, sumStr, sumScaleStr)










#-----------------------------------------------------------------||||||||||||--
#-----------------------------------------------------------------||||||||||||--

class Test:
    def __init__(self):
        #self._testDie()
        #self._testDice()
        self._testNoiseGame()

    def _testDie(self):
        for side in [0, 3, 7, 13]:
            a = Die(side)
            print a
            for x in range(0, 6):
                a.roll()
                print a()

    def _testDice(self):
        games = ([3,4,5], [3,3,3], [0,0,0])

        for diceFmt in games:
            a = DiceUnit(diceFmt)
            print a
            for i in range(0, 6):
                # get a random array
                binArray = []
                for slot in range(0, len(diceFmt)):
                    binArray.append(random.choice([0,1]))
                a.roll(binArray)
                print binArray, a.sum()

    def _testNoiseGame(self):
        noVal = 100
        for gamma in [0,1,2,3,4]:
            x = GameNoise(noVal)
            for i in range(0, 20):
                x.step(gamma)
                print x

if __name__ == '__main__':
    Test()



