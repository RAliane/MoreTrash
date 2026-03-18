#!/home/leo/Documents/Matchgorithm/code/matchgorithm python3

import pandas as pd
import numpy as np
import os
import json

# Peoject  6DoF Module
"""The idea behind this program is to create a linear algebraic quaternion based flight dynamic module that simulate all
six degrees of freedom. This is what allows the script to be rapid, efficient, and easy to understand. 

Program written by Rayan Aliane, and esigned in mindd with S.I. Units initially, however the idea is to later on
to implement converter functions that will allow for the automation of the report.
"""

class dynamics:
	def dynamicsVector(self, north, east, up, pitch, roll, yaw, quat):
		positionVector = np.ndarray([north, east, up])
		orientVector = np.ndarray([pitch, roll, yaw, quat])

	def forceVector(self, lift, thrust, parasiticDrag, inducedDrag,totalDrag, weight, g = 9.80665):
		"""The system is rigged to work in Newtons specifically for force modelling. This means that 
		that if you have to get weigh of the aircraft you have to divide by g."""
		lift = 1/2*rho*v**2**s**cl
		totalDrag = inducedDrag + parasiticDrag
		paraiticDrag = someFormula
		inducedDrag = anotherFormula
		weight = (fuelWeight + armamentWeight + pilotWeight + frameWeight)*g

	def infoSchema(self, data):
		self.data = data[]
		reutn data{
