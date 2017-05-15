## SecuML
## Copyright (C) 2016  ANSSI
##
## SecuML is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## SecuML is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with SecuML. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
import pandas as pd
import random
import scipy

from SecuML.Data import labels_tools
from SecuML.Tools import matrix_tools

class Cluster(object):

    def __init__(self):
        self.instances_ids = []
        self.distances     = []

        self.proba         = []
        self.entropy       = []
        self.likelihood    = []

        self.label         = None
        self.clusters_families_stats = {}
        self.num_annotated_instances = 0

    def numInstances(self):
        return len(self.instances_ids)

    def addInstance(self, instance_id, distance, probas, label, family, annotated):
        self.instances_ids.append(instance_id)
        self.distances.append(distance)
        if probas is not None:
            self.entropy.append(scipy.stats.entropy(probas))
            self.proba.append(max(probas))
        label = labels_tools.labelBooleanToString(label)
        if family is not None:
            key = label + '__' + family
            if key not in self.clusters_families_stats:
                self.clusters_families_stats[key] = 0
            self.clusters_families_stats[key] += 1
        if annotated:
            self.num_annotated_instances += 1

    def finalComputation(self, unknown_cluster_id):
        unknown_cluster_id = self.setClusterLabel(unknown_cluster_id)
        if self.numInstances() != 0:
            self.sortInstances()
        return unknown_cluster_id

    # The list of instances in the cluster are sorted according to :
    #   - the probability of belonging to the cluster (if available)
    #       or
    #   - their distance from the centroid
    def sortInstances(self):
        if len(self.proba) == self.numInstances():
            df = pd.DataFrame({'proba': self.proba,
                               'entropy': self.entropy,
                               'distance': self.distances},
                              index = map(str, self.instances_ids))
            matrix_tools.sortDataFrame(df, 'proba', True, True)
            self.proba     = df.proba.tolist()
            self.entropy   = df.proba.tolist()
        else:
            df = pd.DataFrame({'distance': self.distances},
                              index = map(str, self.instances_ids))
            matrix_tools.sortDataFrame(df, 'distance', True, True)
        self.instances_ids = map(int, df.index.values.tolist())
        self.distances = df.distance.tolist()

    # Pre requisites: len(instances) > num_instances
    #                 num_instances > 0
    def getUncertainInstances(self, instances, num_instances):
        df = pd.DataFrame({'entropy': self.entropy},
                          index = map(str, self.instances_ids))
        selected_df = df.loc[map(str, instances), :]
        matrix_tools.sortDataFrame(selected_df, 'entropy', False, True)
        return map(int, selected_df.index.values.tolist()[:num_instances])

    def setLikelihood(self, likelihood):
        self.likelihood = likelihood

    # Pre requisites: len(instances) > num_instances
    #                 num_instances > 0
    def getHighLikelihoodInstances(self, instances, num_instances):
        df = pd.DataFrame({'likelihood': self.likelihood},
                          index = map(str, self.instances_ids))
        selected_df = df.loc[map(str, instances), :]
        matrix_tools.sortDataFrame(selected_df, 'likelihood', False, True)
        return map(int, selected_df.index.values.tolist()[:num_instances])

    # Pre requisites: len(instances) > num_instances
    #                 num_instances > 0
    def getLowLikelihoodInstances(self, instances, num_instances):
        df = pd.DataFrame({'likelihood': self.likelihood},
                          index = map(str, self.instances_ids))
        selected_df = df.loc[map(str, instances), :]
        matrix_tools.sortDataFrame(selected_df, 'likelihood', False, True)
        return map(int, selected_df.index.values.tolist()[-num_instances:])

    def getLikelihood(self, instances):
        df = pd.DataFrame({'likelihood': self.likelihood},
                          index = map(str, self.instances_ids))
        selected_df = df.loc[map(str, instances), :]
        return selected_df['likelihood'].tolist()

    def setClusterLabel(self, unknown_cluster_id):
        max_occurrences = 0
        for key, v in self.clusters_families_stats.iteritems():
            if v > max_occurrences:
                max_occurrences = v
                self.label = key
        if self.label is None:
            self.label = 'unknown_' + str(unknown_cluster_id)
            return unknown_cluster_id + 1
        else:
            return unknown_cluster_id

    def getClusterLabel(self):
        return self.label

    def getClusterInstances(self, c_e_r, num_instances, drop_instances = None):

        if c_e_r == 'all':
            return self.instances_ids

        if num_instances == 0:
            return []

        if drop_instances is None:
            instances = self.instances_ids
        else:
            instances = [x for x in self.instances_ids if x not in drop_instances]

        if len(instances) < num_instances:
            return instances

        if c_e_r == 'center':
            if len(self.likelihood) == self.numInstances():
                return self.getHighLikelihoodInstances(instances, num_instances)
            else:
                return instances[:num_instances]
        elif c_e_r == 'anomalous':
            if len(self.likelihood) == self.numInstances():
                return self.getLowLikelihoodInstances(instances, num_instances)
            else:
                return instances[-num_instances:]
        elif c_e_r == 'random':
            return random.sample(instances, num_instances)
        elif c_e_r == 'uncertain':
            return self.getUncertainInstances(instances, num_instances)
        else:
            raise ValueError('Invalid argument value c_e_r %s' % (c_e_r))

    # c: center
    # e: edge (does not return instances from the center)
    # r: random (does not return instances from the center and the edge)
    # An instance cannot be in two sets among c, e and r.
    def getClusterInstancesVisu(self, num_instances, rand = False, drop_instances = None):
        if drop_instances is None:
            drop_instances = []
        num_center = int(num_instances/2)
        num_edge = num_instances - num_center
        c_e_r = {}
        c_e_r['c'] = self.getClusterInstances('center', num_center, drop_instances = drop_instances)
        c_e_r['e'] = self.getClusterInstances('anomalous', num_edge, drop_instances = drop_instances + c_e_r['c'])
        if rand:
            num_random = num_instances
            c_e_r['r'] = self.getClusterInstances('random', num_random,
                    drop_instances = drop_instances + c_e_r['c'] + c_e_r['e'])
        else:
            c_e_r['r'] = []
        return c_e_r

    def getClusterLabelsFamilies(self, cursor, label_experiment_id):
        labels_family = labels_tools.getLabelsFamilies(cursor, label_experiment_id, self.instances_ids)
        return labels_family

    def getClusterLabelFamilyIds(self, label, family, cursor, experiment_label_id):
        if label == 'unknown' and (family is None or family == 'unknown'):
            ids = labels_tools.getUnlabeledIds(cursor, experiment_label_id,
                    instance_ids = self.instances_ids)
        else:
            ids = labels_tools.getLabelFamilyIds(cursor,
                    experiment_label_id, label, family,
                    instance_ids = self.instances_ids)
        return ids

    ## Remove semi automatic labels
    ## Annotations are preserved
    def removeClusterLabel(self, num_results, cursor, experiment_label_id):
        for instance_id in self.instances_ids:
            if not labels_tools.hasAnnotation(cursor, instance_id, experiment_label_id):
                labels_tools.removeLabel(cursor, experiment_label_id, instance_id)

    def addClusterLabel(self, num_results, label, family, cursor,
            experiment_label_id, label_iteration, label_method):
        for instance_id in self.instances_ids:
            labels_tools.addLabel(cursor, experiment_label_id, instance_id, label, family,
                    label_iteration, label_method, False)

    def toJson(self, drop_instances = None):
        obj = {}
        if drop_instances is None:
            obj['instances_ids'] = self.instances_ids
            obj['distances']     = self.distances
        else:
            obj['instances_ids'] = []
            obj['distances']     = []
            for i in range(len(self.instances_ids)):
                instance_id = self.instances_ids[i]
                if instance_id in drop_instances:
                    continue
                else:
                    obj['instances_ids'].append(instance_id)
                    obj['distances'].append(self.distances[i])
        obj['label']                   = self.label
        return obj

    @staticmethod
    def fromJson(obj):
        cluster = Cluster()
        cluster.instances_ids           = obj['instances_ids']
        cluster.distances               = obj['distances']
        cluster.label                   = obj['label']
        return cluster