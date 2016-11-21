from PySide.QtCore import *
from PySide.QtGui import *
from pyrecon.gui import mergetool
from pyrecon import openSeries
from pyrecon.classes import Series, Section
from shapely.geometry import box, LinearRing, LineString, Point, Polygon
import os
from pyrecon.tools import reconstruct_writer

TOLERANCE = 1 + 2**-17

class PyreconMainWindow(QMainWindow):
    '''Main PyRECONSTRUCT window.'''
    def __init__(self, *args, **kwargs):
        QMainWindow.__init__(self)
        self.setWindowTitle('MergeTraces')
        self.show()
        newSize = QDesktopWidget().availableGeometry().size() / 4
        self.resize( newSize )
        self.statusBar().showMessage('Ready! Welcome to PyRECONSTRUCT')
        self.loadMergeTool()
    def loadMergeTool(self):
        loadDialog = SingleSeriesLoad() # User locates 1 series
        s1 = openSeries(loadDialog.output)
        mTraces = createMergeTraces(s1)
        self.setCentralWidget( MergeSetWrapper(mTraces) )

class BrowseWidget(QWidget):
    '''Provides a QLineEdit and button for browsing through a file system. browseType can be directory, file or series but defaults to directory.'''
    def __init__(self, browseType='directory'):
        QWidget.__init__(self)
        self.loadObjects(browseType)
        self.loadFunctions(browseType)
        self.loadLayout()
    def loadObjects(self, browseType):
        # Path entry area
        self.path = QLineEdit()
        if browseType == 'directory':
            title = 'Enter or browse path to directory'
        elif browseType == 'series':
            title = 'Enter or browse path'
        else:
            title = 'Enter or browse path to file'
        self.path.setText(title)
        # Browse button
        self.browseButton = QPushButton()
        self.browseButton.setText('Browse')
    def loadFunctions(self, browseType):
        if browseType == 'directory':
            self.browseButton.clicked.connect( self.browseDir )
        elif browseType == 'series':
            self.browseButton.clicked.connect( self.browseSeries )
        else:
            self.browseButton.clicked.connect( self.browseFile )
    def loadLayout(self):
        hbox = QHBoxLayout()
        hbox.addWidget(self.path)
        hbox.addWidget(self.browseButton)
        self.setLayout(hbox)
    def browseDir(self):
        dirName = QFileDialog.getExistingDirectory(self)
        self.path.setText( str(dirName) )
    def browseFile(self):
        fileName = QFileDialog.getOpenFileName(self, "Open File", "/home/")
        self.path.setText( str(fileName[0]) )
    def browseSeries(self):
        fileName = QFileDialog.getOpenFileName(self, "Open Series", "/home/", "Series File (*.ser)")
        self.path.setText( str(fileName[0]) )

class BrowseOutputDirectory(QDialog):
    '''Starts a popup dialog for choosing a directory in which to save a series'''
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
        self.exec_()
    def loadObjects(self):
        self.path = BrowseWidget()
        self.doneBut = QPushButton()
    def loadFunctions(self):
        self.doneBut.setText('Write Series')
        self.doneBut.clicked.connect( self.finish )
    def loadLayout(self):
        main = QVBoxLayout()
        main.addWidget(self.path)
        main.addWidget(self.doneBut)
        self.setLayout(main)
    def finish(self):
        self.output = str(self.path.path.text())
        if 'Enter or browse' not in self.output or self.output == '':
            self.done(1)
        else:
            msg=QMessageBox()
            msg.setText('Invalid output directory: '+str(self.output))
            msg.exec_()
            return

class SingleSeriesLoad(QDialog):
    '''Dialog for loading series files into memory as pyrecon.classes.Series objects'''
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
        self.exec_()
    def loadObjects(self):
        self.series1 = BrowseWidget(browseType='series')
        self.closeButton = QPushButton()
        self.closeButton.setText('Load Series')
    def loadFunctions(self):
        self.closeButton.clicked.connect( self.loadClose )
    def loadLayout(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.series1)
        vbox.addWidget(self.closeButton)
        self.setLayout(vbox)
    def loadClose(self):
        # Add paths to self.output
        self.output = ( str(self.series1.path.text())
                        )
        self.close()

    if __name__ == '__main__':
        app = QApplication.instance()
        if app == None:
            app = QApplication([])
        a = PyreconMainWindow()
        app.exec_()

class MergeSetWrapper(QWidget):
    '''This class is a single widget that contains all necessary widgets for resolving conflicts in a MergeSet and handles the signal/slots between them.'''
    def __init__(self, MergeSet):
        QWidget.__init__(self)
        self.setWindowTitle('PyRECONSTRUCT mergeTraces')
        self.merge = MergeSet
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
        self.loadResolutions()
    def loadObjects(self):
        self.navigator = MergeSetNavigator(self.merge) # Buttons and list of MergeObjects
        self.resolutionStack = QStackedWidget() # Contains all of the resolution wrappers
    def loadFunctions(self):
        # QStackedWidget needs to respond to setList.itemClicked
        self.navigator.setList.itemClicked.connect( self.updateCurrent )
    def loadLayout(self):
        container = QHBoxLayout()
        container.addWidget(self.navigator)
        container.addWidget(self.resolutionStack)
        self.setLayout(container)
    def loadResolutions(self):
        if self.merge is not None:
            for itemIndex in range( self.navigator.setList.count() ):
                self.resolutionStack.addWidget( self.navigator.setList.item(itemIndex).resolution )
            self.navigator.setList.item(0).clicked() # Show MergeSeries
    def updateCurrent(self, item):
        '''Updates currently shown resolution based on an item received from self.navigator.setList'''
        self.resolutionStack.setCurrentIndex( self.navigator.setList.indexFromItem(item).row() )

class MergeSetNavigator(QWidget):
    '''This class provides buttons for loading and saving MergeSets as well as a list for choosing current conflict to manage.'''
    def __init__(self, MergeSet):
        QWidget.__init__(self)
        self.merge = MergeSet
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
    def loadObjects(self):
        self.loadButton = QPushButton('&Change MergeSet')
        self.loadButton.setMinimumHeight(50)
        self.setList = MergeSetList(self.merge)
        self.saveButton = QPushButton('&Save')
        self.saveButton.setMinimumHeight(50)
    def loadFunctions(self):
        self.loadButton.clicked.connect( self.load )
        self.saveButton.clicked.connect( self.save )
    def loadLayout(self):
        container = QVBoxLayout()
        container.addWidget( self.loadButton )
        container.addWidget( self.setList )
        container.addWidget( self.saveButton )
        self.setLayout(container)

    def load(self):
        # Load SingleSeriesBrowse widget
        loadDialog = SingleSeriesLoad()
        s1 = openSeries(loadDialog.output) # Create Series objects from path
        # Make MergeSeries, MergeSection objects
        mSeries = MergeSeries(s1)
        mSections = []
        for i in range(len(s1.sections)):
            mSections.append( MergeSection(s1.sections[i]))
        # Clear setList
        (self.setList).clear()
        # Create setList with new MergeSet
        (self.setList).merge = MergeSet(mSeries, mSections)
        #=== Could not figure out how to make new one and replace, use init functions instead
        (self.setList).loadObjects()
        (self.setList).loadFunctions()

    def save(self):
        # Check for conflicts
        if self.checkConflicts():
            a = BrowseOutputDirectory()
            outpath = a.output
            # Go through all setList items and save to outputdir
            self.writeMergeObjects(outpath)
        #===
        msg = QMessageBox()
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setText('Would you like to close mergeTool?')
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            self.parentWidget().close()
            self.parentWidget().parentWidget().done(1) #=== doesnt work from MainWindow
        elif ret == QMessageBox.No:
            return

    def checkConflicts(self):
        unresolved_list = [] # list of unresolved conflict names
        for i in range(self.setList.count()):
            item = self.setList.item(i)
            if item.isResolved():
                continue
            else:
                unresolved_list.append(item.merge.name)
        # Bring up dialog for unresolved conflicts
        if len(unresolved_list) > 0:
            msg = QMessageBox()
            msg.setText('Not all conflicts were resolved:\n'+'\n'.join(unresolved_list))
            msg.setInformativeText('Would you like to default unresolved conflicts as unchanged for these conflicts?')
            msg.setStandardButtons( QMessageBox.Ok | QMessageBox.Cancel)
            ret = msg.exec_()
            return (ret == QMessageBox.Ok)
        else:
            return True
    def writeMergeObjects(self, outpath):
        self.merge.writeMergeSet(outpath)

class MergeSetList(QListWidget):
    '''This class is a specialized QListWidget that contains MergeSetListItems.'''
    def __init__(self, MergeSet):
        QListWidget.__init__(self)
        self.merge = MergeSet
        self.loadObjects()
        self.loadFunctions()
    def loadObjects(self):
        # Load MergeObjects into list
        for MergeSection in self.merge.sectionMerges: # Load MergeSections
            self.addItem( MergeSetListItem(MergeSection) )
    def loadFunctions(self):
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # What to do when item clicked?
        self.itemClicked.connect( self.clicked )
        # What to do when item doubleClicked?
        self.itemDoubleClicked.connect( self.doubleClicked )
    def clicked(self, item):
        item.clicked()
        self.refreshAll()
    def refreshAll(self): #=== may freeze with higher num items?
        '''Refreshes (item.refresh()) all items in the list'''
        for i in range( self.count() ):
            self.item(i).refresh()
    def doubleClicked(self, item):
        '''double-clicking a mergeItem displays a small menu allowing the user to use quick merge options.'''
        items = self.selectedItems()
        # Pop open menu for user selection
        quickmerge = QuickMergeMenu()
        action = quickmerge.exec_( QCursor.pos() )
        # Perform selected action
        if action == quickmerge.selAAction:
            self.quickMergeA(items)
        elif action == quickmerge.selBAction:
            self.quickMergeB(items)
        elif action == quickmerge.selABContsActionA:
            self.quickMergeABContsA(items)
        elif action == quickmerge.selABContsActionB:
            self.quickMergeABContsB(items)
    def quickMergeA(self, items):
        '''Selects A (left) version for all conflicts in items.'''
        for item in items:
            if item.merge.__class__.__name__ == 'MergeSection':
                item.resolution.attributes.chooseLeft.click()
                item.resolution.images.chooseLeft.click()
                item.resolution.contours.onlyAContours()
            elif item.merge.__class__.__name__ == 'MergeSeries':
                item.resolution.attributes.chooseLeft.click()
                item.resolution.contours.chooseLeft.click()
                item.merge.zcontours = item.merge.series1.zcontours #===
            item.refresh()

    def quickMergeB(self, items):
        '''Selects B (right) version for all conflicts in items.'''
        for item in items:
            if item.merge.__class__.__name__ == 'MergeSection':
                item.resolution.attributes.chooseRight.click()
                item.resolution.images.chooseRight.click()
                item.resolution.contours.onlyBContours()
            elif item.merge.__class__.__name__ == 'MergeSeries':
                item.resolution.attributes.chooseRight.click()
                item.resolution.contours.chooseRight.click()
                item.merge.zcontours = item.merge.series2.zcontours #===
            item.refresh()
    def quickMergeABContsA(self, items): #===
        '''This completes the merge resolution by selecting the A (left) version of non-contour conflicts (attributes & images). For contour conflicts, this selects BOTH (left & right) for overlaps and uniques.'''
        for item in items:
            if item.merge.__class__.__name__ == 'MergeSection':
                item.resolution.attributes.chooseLeft.click()
                item.resolution.images.chooseLeft.click()
                item.resolution.contours.allContours()
            elif item.merge.__class__.__name__ == 'MergeSeries':
                item.resolution.attributes.chooseLeft.click()
                item.resolution.contours.chooseLeft.click()
                # zconts
                item_1_uniques, item_2_uniques, ovlps = item.merge.getCategorizedZContours()
                item.merge.zcontours = item_1_uniques+item_2_uniques+ovlps
            item.refresh()
    def quickMergeABContsB(self, items): #===
        '''This completes the merge resolution by selection the B (right) version of non-contour conflicts (attributes & images). For contour conflicts, this selects BOTH (left & right) for overlaps and uniques.'''
        for item in items:
            if item.merge.__class__.__name__ == 'MergeSection':
                item.resolution.attributes.chooseRight.click()
                item.resolution.images.chooseRight.click()
                item.resolution.contours.allContours()
            elif item.merge.__class__.__name__ == 'MergeSeries':
                item.resolution.attributes.chooseRight.click()
                item.resolution.contours.chooseRight.click()
                # zconts
                item_1_uniques, item_2_uniques, ovlps = item.merge.getCategorizedZContours()
                item.merge.zcontours = item_1_uniques+item_2_uniques+ovlps
            item.refresh()

class MergeSetListItem(QListWidgetItem):
    '''This is a specialized QListWidgetItem that contains either a MergeSection or MergeSeries object and the widget used for its resolution'''
    def __init__(self, MergeObject):
        QListWidgetItem.__init__(self)
        self.merge = MergeObject
        self.resolution = None
        self.loadDetails()
        self.refresh() # update colors
    def loadDetails(self):
        self.setText(self.merge.name)
        self.setFont(QFont("Arial", 14))
        # Resolution (type specific MergeWrapper)
        if self.merge.__class__.__name__ == 'MergeSection':
            self.resolution = SectionMergeWrapper(self.merge)
        else:
            print ("Series loaded...")
            pass
    def clicked(self):
        if self.merge.isDone():
            self.setBackground(QColor('lightgreen'))
        elif self.merge.doneCount() > 0:
            self.setBackground(QColor('yellow'))
        else:
            self.setBackground(QColor('red'))

    def doubleClicked(self):
        print 'MergeSetListItem.doubleClicked()'
        # Necessary? #===
    def isResolved(self):
        '''Returns true if merge conflicts are resolved.'''
        return self.resolution.merge.isDone()
    def refresh(self): #===
        '''Update colors'''
        if self.isResolved():
            self.setBackground(QColor('lightgreen'))
        elif self.resolution.doneCount() > 0:
            self.setBackground(QColor('yellow'))
        else:
            self.setBackground(QColor('red'))

class QuickMergeMenu(QMenu):
    def __init__(self, parent=None):
        QMenu.__init__(self, parent)
        self.setTitle('Quick-merge')
        self.createActions()
        self.addActions()
    def createActions(self):
        # - Options for when doubleClicked
        self.selAAction = QAction(QIcon(), 'Select all left', self) # Select the A versions of all
        self.selBAction = QAction(QIcon(), 'Select all right', self) # Select the B versions of all
        self.selABContsActionA = QAction(QIcon(), 'Select both contours, left atts and images', self) # Select both for contour conflicts, A for rest
        self.selABContsActionB = QAction(QIcon(), 'Select both contours, right atts and images', self) # Select both for contour conflicts, B for rest
        # - ToolTips
        self.selAAction.setToolTip('Select the left version of everything for this item(s)')
        self.selBAction.setToolTip('Select the right version of everything for this item(s)')
        self.selABContsActionA.setToolTip('Select left&&right contours, left for images and attributes')
        self.selABContsActionB.setToolTip('Select left&&right contours, right for images and attributes')
    def addActions(self):
        # - Add options to menu
        self.addAction(self.selAAction)
        self.addAction(self.selBAction)
        self.addAction(self.selABContsActionA)
        self.addAction(self.selABContsActionB)

def start():
    """Begin GUI application (pyrecon.gui.main)"""
    app = QApplication.instance()
    if app is None:  # Create QApplication if doesn"t exist
        app = QApplication([])
    gui = PyreconMainWindow()
    app.exec_()  # Start event-loop

def createMergeTraces(series1):
  """Return a file with traces merged."""
  m1 = MergeSeries(name=series1.name, series1=series1)

  m_secs = []
  for section in series1.sections:
    section_traces = MergeSection(name=section.name, section1=section)
    m_secs.append(section_traces)

  
  mergedTraceSet = MergeSet(name=m1.name, merge_series=m1, section_merges=m_secs)
  return mergedTraceSet

class MergeSet(object):
    """Class for merging data Series and Section data."""

    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.seriesMerge = kwargs.get("merge_series")
        self.sectionMerges = kwargs.get("section_merges", [])

    def isDone(self):
        sections_done = True
        for section in self.sectionMerges:
            if not section.isDone():
                sections_done = False
                break
        return (self.seriesMerge.isDone() and sections_done)


    def writeMergeSet(self, outpath):
        """Writes self.seriesMerge and self.sectionMerges to XML"""
        merged_series = self.seriesMerge.toSeries()
        merged_series.name = self.seriesMerge.name.replace(".ser", "")
        merged_series.name = str(merged_series.name)+"merged"
        for mergeSec in self.sectionMerges:
            merged_series.sections.append(mergeSec.toSection())
        reconstruct_writer.write_series(merged_series, outpath, sections=True)
        print "Done!" 

class MergeSection(object):

  def __init__(self, *args, **kwargs):

      self.name = kwargs.get("name")
      self.section1 = kwargs.get("section1")

      # Merged stuff
      self.attributes = self.section1.attributes()
      self.images = self.section1.images
      self.contours = None

      # Contours conflict resolution stuff
      self.section_1_unique_contours = None
      self.definite_shared_contours = None
      self.potential_shared_contours = None


      self.checkConflicts()
  
  def checkConflicts(self):
    # Are contours equivalent?
    #when loaded in here, contours are fine, no duplicates

    separated_contours = self.getCategorizedContours(include_overlaps=True)
    
    
    self.section_1_unique_contours = separated_contours[0]
    self.definite_shared_contours = separated_contours[1]
    self.potential_shared_contours = separated_contours[2]
    self.images = self.section1.images

#    print ("unique contours")
#    for item in self.section_1_unique_contours:
#      
#        print(item.name)


#    print ("definite contours")
#    for item in self.definite_shared_contours:
#      
#        print(item.name)

#    print ("potential contours")
#    for item in self.potential_shared_contours:
#      if isinstance (item, list):
#        for item2 in item:
#          print(item2.name)
#      else:
#        print (item.name)

  def getCategorizedContours(self, threshold=(1 + 2**(-17)), sameName=True, include_overlaps=False):
      """Returns list of mutually overlapping contours in a Section object."""
      complete_overlaps = []
      potential_overlaps = []

      # Compute overlaps
      overlaps = []
      overlapsA = []
      overlapsB = []

      counter1 = 0
      counter2 = 0

      for idx, contA in enumerate(self.section1.contours):
        for idx2, contB in enumerate(self.section1.contours):


          if [contB, contA] in potential_overlaps:
            continue
    
          if idx == idx2:
            continue
        
          if contA.name != contB.name:
              continue
          if contA.shape.type != contB.shape.type:
              continue

          if not is_contacting(contA.shape, contB.shape):
              continue
          elif is_exact_duplicate(contA.shape, contB.shape):
              overlapsA.append(contA)
              overlapsB.append(contB)
              if (contB) not in complete_overlaps:
                complete_overlaps.append(contA)
              continue
          if is_potential_duplicate(contA.shape, contB.shape):
              overlapsA.append(contA)
              overlapsB.append(contB)
              potential_overlaps.append([contA, contB])

      if include_overlaps:
          # Return unique conts from section1,
          # completely overlapping contours, and incompletely overlapping
          # contours
          new_potential_overlaps = []
          for contA, contB in potential_overlaps:
              if (contA in complete_overlaps and contB in complete_overlaps):
                  continue
              else:
                  new_potential_overlaps.append([contA, contB])
          potential_overlaps = new_potential_overlaps
          return (
              [cont for cont in self.section1.contours if cont not in overlapsA and overlapsB],
              complete_overlaps,
              potential_overlaps
          )
      else:
          return (
              [cont for cont in self.section1.contours if cont not in (overlapsA or overlapsB)],
              )

  def toSection(self):
      """Return a Section object that resolves the merge.

      If not resolved (None), defaults to the self.section1 version
      """

#    print ("unique contours")
#    for item in self.section_1_unique_contours:
#      
#        print(item.name)


#    print ("definite contours")
#    for item in self.definite_shared_contours:
#      
#        print(item.name)

#    print ("potential contours")
#    for item in self.potential_shared_contours:
#      if isinstance (item, list):
#        for item2 in item:
#          print(item2.name)
#      else:
#        print (item.name)


      attributes = self.attributes if self.attributes is not None else self.section1.attributes()
      images = self.images if self.images is not None else self.section1.images
      contours = self.contours if self.contours is not None else self.section1.contours
      return Section(images=images, contours=contours, **attributes)

  def isDone(self):
      """Boolean indicating status of merge."""
      return (self.attributes is not None and
              self.images is not None and
              self.contours is not None)

  def doneCount(self):
      """Number of resolved issues"""
      return (self.attributes is not None,
              self.images is not None,
              self.contours is not None).count(True)

class MergeSeries(object):
  def __init__(self, **kwargs):
      self.name = kwargs.get("name")
      # Series to be used
      self.series1 = kwargs.get("series1")

      # Merged stuff
      self.attributes = None
      self.contours = None
      self.zcontours = None

  def toSeries(self):
      """Return a Series object that resolves the merge.
      If not resolved (None), defaults to self.series1 version
      """
      attributes = self.attributes if self.attributes is not None else self.series1.attributes()
      contours = self.contours if self.contours is not None else self.series1.contours
      zcontours = self.zcontours if self.zcontours is not None else self.series1.zcontours
      return Series(contours=contours, zcontours=zcontours, **attributes)

#def createMergeSet(series1, series2):  # TODO: needs multithreading
#    """Return a MergeSet from two Series."""
#    if len(series1.sections) != len(series2.sections):
#        raise Exception("Series do not have the same number of Sections.")

#    m_ser = MergeSeries(
#        name=series1.name,
#        series1=series1,
#        series2=series2,
#    )
#    m_secs = []
#    for section1, section2 in zip(series1.sections, series2.sections):
#        if section1.index != section2.index:
#            raise Exception("Section indices do not match.")
#        merge_section = MergeSection(
#            name=section1.name,
#            section1=section1,
#            section2=section2,
#        )
#        m_secs.append(merge_section)

#    return MergeSet(
#        name=m_ser.name,
#        merge_series=m_ser,
#        section_merges=m_secs,
#    )



def is_contacting(shape1, shape2):
    """Return True if two shapes are contacting."""
    if isinstance(shape1, Point) and isinstance(shape2, Point):
        # TODO: investigate more sophisticated comparison
        return shape1.equals(shape2)

    elif isinstance(shape1, LineString) and isinstance(shape2, LineString):
        # shape1.almost_equals(shape2)?
        return shape1.almost_equals(shape2)

    elif isinstance(shape1, Polygon) and isinstance(shape2, Polygon):
        this_box = box(*shape1.bounds)
        other_box = box(*shape2.bounds)
        if not this_box.intersects(other_box) and not this_box.touches(other_box):
            return False
        else:
            return True

    raise Exception("No support for shape type(s): {}".format(
        set([shape1.type, shape2.type])))


def is_exact_duplicate(shape1, shape2, threshold=TOLERANCE):
    """Return True if two shapes are exact duplicates (within tolerance)."""
    if isinstance(shape1, Point) and isinstance(shape2, Point):
        # TODO: investigate more sophisticated comparison
        return shape1.equals(shape2)

    elif isinstance(shape1, Polygon) and isinstance(shape2, Polygon):
        if shape1.has_z and shape2.has_z:
            return shape1.exterior.equals(shape2.exterior)
        else:
            if not shape1.is_valid or not shape2.is_valid:
                return False
            if is_reverse(shape2) != is_reverse(shape2):
                # Reverse traces are not duplicates of non-reverse
                return False
            area_of_union = shape1.union(shape2).area
            area_of_intersection = shape1.intersection(shape2).area
            if not area_of_intersection:
                return False
            union_over_intersection = area_of_union / area_of_intersection
            if union_over_intersection >= threshold:
                # Potential duplicate
                return False
            elif union_over_intersection < threshold:
                return True

    elif isinstance(shape1, LineString) and isinstance(shape2, LineString):
        # TODO: investigate more sophisticated comparison
        return shape1.equals(shape2)

    raise Exception("No support for shape type(s): {}".format(
        set([shape1.type, shape2.type])))


def is_potential_duplicate(shape1, shape2, threshold=TOLERANCE):
    """Return True if two shapes are potential overlaps (exceed tolerance)."""
    if isinstance(shape1, Point) and isinstance(shape2, Point):
        # TODO: investigate more sophisticated comparison
        return shape1.almost_equals(shape2) and not shape1.equals(shape2)

    elif isinstance(shape1, Polygon) and isinstance(shape2, Polygon):

        if not shape1.is_valid or not shape2.is_valid:
            return False
        if shape1.has_z or shape2.has_z:
            raise Exception(
                "is_potential_duplicate does not support 3D polygons")
        if is_reverse(shape2) != is_reverse(shape2):
            # Reverse traces are not duplicates of non-reverse
            return False
        area_of_union = shape1.union(shape2).area
        area_of_intersection = shape1.intersection(shape2).area
        if not area_of_intersection:
            return False
        union_over_intersection = area_of_union / area_of_intersection
        if union_over_intersection >= threshold:
            return True
        else:
            return False

    elif isinstance(shape1, LineString) and isinstance(shape2, LineString):
        # TODO: investigate more sophisticated comparison
        return shape1.almost_equals(shape2) and not shape1.equals(shape2)

    raise Exception("No support for shape type(s): {}".format(
        set([shape1.type, shape2.type])))



def get_bounding_box(shape):
    """Return bounding box of shapely shape."""
    minx, miny, maxx, maxy = shape.bounds
    return box(minx, miny, maxx, maxy)


def is_reverse(shape):
    """Return True if shape is a RECONSTRUCT reverse trace (negative area)."""
    if isinstance(shape, Polygon):
        ring = LinearRing(shape.exterior.coords)
        # RECONSTRUCT is opposite for some reason
        return not ring.is_ccw
    return False

from copy import deepcopy

import numpy as np
from PySide.QtCore import *
from PySide.QtGui import *

import pyrecon


# SECTION CONFLICT RESOLUTION GUI WRAPPER
class SectionMergeWrapper(QTabWidget):
    '''sectionWrapper is a TabWidget. It contains multiple widgets that can be swapped via their tabs.'''
    def __init__(self, MergeSection):
        QTabWidget.__init__(self)
        self.merge = MergeSection
        self.loadObjects()
    def loadObjects(self):
        # Load widgest to be used as tabs
        self.contours = SectionContourHandler(self.merge)
        # Add widgets as tabs
        self.addTab(self.contours, '&Contours')
    def doneCount(self):
        return self.merge.doneCount()

# - Contours
class SectionContourHandler(QWidget):
    def __init__(self, MergeSection):
        QWidget.__init__(self)
        self.merge = MergeSection
        # Contours
        # - Unique contours from each section
	self.section_1_unique_contours = self.merge.section_1_unique_contours
	# - Complete overlap, and conflicting overlap contours
	self.definite_shared_contours = self.merge.definite_shared_contours
	self.potential_shared_contours = self.merge.potential_shared_contours
        # Load UI
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
        self.checkEquivalency()
    def checkEquivalency(self):
        '''Checks to see if the MergeSections' checkConflicts() function automatically handled this. SHOULD ONLY BE RUN IN INIT'''
        if self.merge.contours is not None:
            txt = 'Contours are equivalent, no conflict.'
            self.doneBut.setText(txt)
            self.doneBut.setStyleSheet('background-color:lightgreen;')
    def loadObjects(self):
        # List contours in their appropriate listWidgets
        self.inPotential = QListWidget(self)
        self.inUniqueOvlps = QListWidget(self)

        self.outPotential = QListWidget(self)
        self.outUniqueOvlps = QListWidget(self)



        self.moveSelectedP = QPushButton(self)
        self.moveSelectedAO = QPushButton(self)


        self.doneBut = QPushButton(self) # Merge button

    def loadFunctions(self):
        # Load tables with contour objects

        self.loadTable(self.inPotential, self.potential_shared_contours)
        self.loadTable(self.outUniqueOvlps, self.definite_shared_contours)
        self.loadTable(self.outUniqueOvlps, self.section_1_unique_contours)
        for table in [self.inUniqueOvlps, self.inPotential, self.outUniqueOvlps, self.outPotential]:
            table.setSelectionMode(QAbstractItemView.ExtendedSelection)
            table.itemDoubleClicked.connect(self.doubleClickCheck)
        self.doneBut.setText('Save Current Status')
        self.doneBut.clicked.connect( self.finish )
        self.doneBut.setMinimumHeight(50)
        self.moveSelectedAO.setText('Move Selected')
        self.moveSelectedP.setText('Move Selected')
        self.moveSelectedAO.clicked.connect( self.moveItems )
        self.moveSelectedP.clicked.connect( self.moveItems )
    def loadLayout(self):
        container = QVBoxLayout()
        secNameContainer = QHBoxLayout()
        secNameContainer.setAlignment(Qt.AlignHCenter)
        secNameContainer.addWidget(QLabel(str(self.merge.section1.name)))
        columnContainer = QHBoxLayout()

        labelContainer = QVBoxLayout()
        labelContainer.addWidget(QLabel('Input'))
        labelContainer.addWidget(QLabel('Output'))
        columnContainer.addLayout(labelContainer)

        potential_overlapsColumn = QVBoxLayout()
        potential_overlapsLabel = QLabel('Potential Duplicate Contours')
        potential_overlapsColumn.addWidget(potential_overlapsLabel)
        potential_overlapsColumn.addWidget(self.inPotential)
        potential_overlapsColumn.addWidget(self.moveSelectedP)
        potential_overlapsColumn.addWidget(self.outPotential)
        columnContainer.addLayout(potential_overlapsColumn)

        section_1_unique_overlapsColumn = QVBoxLayout()
        section_1_unique_contoursLabel = QLabel('Unique or Exact Duplicate Contours')
        section_1_unique_overlapsColumn.addWidget(section_1_unique_contoursLabel)
        section_1_unique_overlapsColumn.addWidget(self.inUniqueOvlps)
        section_1_unique_overlapsColumn.addWidget(self.moveSelectedAO)
        section_1_unique_overlapsColumn.addWidget(self.outUniqueOvlps)
        columnContainer.addLayout(section_1_unique_overlapsColumn)


        container.addLayout(secNameContainer)
        container.addLayout(columnContainer)
        container.addWidget(self.doneBut)
        self.setLayout(container)
    def loadTable(self, table, items):
        '''Load <table> with <items>'''
        for item in items:
            listItem = contourTableItem(item, table, [self.merge.section1.images[-1], self.merge.section1.images[-1]])
            if item.__class__.__name__ == 'Contour':
              if item in self.section_1_unique_contours: # Unique contour
                  self.outUniqueOvlps.addItem(listItem)
                  listItem.setBackground(QColor('lightgreen'))
                  continue
            elif isinstance(item, list):
              if item in self.potential_shared_contours:
                      # Item can be a contour or list of 2 contours, they are handled differently in contourTableItem class upon initialization
                listItem.setBackground(QColor('red'))
        
            table.addItem(listItem)
    def doubleClickCheck(self, item):
        item.clicked() # See contourTableItem class
        if item.table == self.inPotential:         
          self.moveItems(potentialmov=True)
        else:
          potentialmov=False
        self.doneBut.setStyleSheet(QWidget().styleSheet())
    def moveItems(self, potentialmov=False):
        # Move items in which table(s)?
        if self.sender() == self.moveSelectedAO:
            inTable = self.inUniqueOvlps
            outTable = self.outUniqueOvlps
        elif (self.sender() == self.moveSelectedP) or potentialmov:
                        
            inTable = self.inPotential
            outTable = self.outPotential

      
        # Now move items
        selectedIn = inTable.selectedItems()
        selectedOut = outTable.selectedItems()

        if potentialmov:
          for item in selectedIn:
              outTable.addItem( inTable.takeItem(inTable.row(item)) )  
        else:
          for item in selectedIn:
              outTable.addItem( inTable.takeItem(inTable.row(item)) )
          for item in selectedOut:
              inTable.addItem( outTable.takeItem(outTable.row(item)) )
        inTable.clearSelection()
        outTable.clearSelection()
        self.doneBut.setStyleSheet(QWidget().styleSheet()) # Button not green, indicates lack of save
        self.merge.contours = None # Reset MergeSection.contours
    def finish(self):
        # Check ovlp table for unresolved conflicts (red)

        oUO = [] # Unique & Definite
        for i in range(self.outUniqueOvlps.count()):
            oUO.append(self.outUniqueOvlps.item(i))
        oP = [] # Potential
        for i in range(self.outPotential.count()):
            oP.append(self.outPotential.item(i))

        # set self.output to chosen contours
        output = [item.contour for item in oP]+[item.contour for item in oUO]
        self.merge.contours = output
        self.doneBut.setStyleSheet('background-color:lightgreen;') # Button to green
    # Quick merge functions
    def onlyAContours(self): #===
        self.allUniqueA()
        self.noUniqueB()
        # move all ovlps to outOvlps
        for i in range(self.inOvlp.count()):
            self.inOvlp.item(i).setSelected(True)
        self.moveSelectedO.click()
        # Select A versions for ovlps
        for i in range(self.outOvlp.count()):
            self.outOvlp.item(i).forceResolution(1)
        self.doneBut.click()
    def onlyBContours(self): #===
        self.allUniqueB()
        self.noUniqueA()
        # move all ovlps to outOvlps
        for i in range(self.inOvlp.count()):
            self.inOvlp.item(i).setSelected(True)
        self.moveSelectedO.click()
        # Select A versions for ovlps
        for i in range(self.outOvlp.count()):
            self.outOvlp.item(i).forceResolution(2)
        self.doneBut.click()
    def allContours(self): #===
        '''choose both contours for all conflicts and move everything to output'''
        self.allUniqueA()
        self.allUniqueB()
        self.allOvlps()
        self.doneBut.click()
    def allOvlps(self):
        '''Select both versions of all overlaps and move to output'''
        for i in range(self.inOvlp.count()):
            self.inOvlp.item(i).setSelected(True)
        self.moveSelectedO.click()
        for i in range(self.outOvlp.count()):
            self.outOvlp.item(i).forceResolution(3)
    def allUniqueA(self):
        '''moves all unique A contours to output'''
        for i in range(self.inUniqueA.count()):
            self.inUniqueA.item(i).setSelected(True)
        self.moveSelectedA.click()
    def allUniqueB(self):
        '''moves all unique B contours to output'''
        for i in range(self.inUniqueB.count()):
            self.inUniqueB.item(i).setSelected(True)
        self.moveSelectedB.click()
    def noUniqueA(self):
        '''returns all outUniqueA items to inUniqueA'''
        for i in range(self.outUniqueA.count()):
            self.outUniqueA.item(i).setSelected(True)
        self.moveSelectedA.click()
    def noUniqueB(self):
        '''returns all outUniqueB items to inUniqueB'''
        for i in range(self.outUniqueB.count()):
            self.outUniqueB.item(i).setSelected(True)
        self.moveSelectedB.click()

class contourPixmap(QLabel):
    '''QLabel that contains a contour drawn on its region in an image'''
    def __init__(self, image, contour, pen=Qt.red):
        QLabel.__init__(self)
        self.image = image
        self.pixmap = QPixmap( image._path+image.src )
        self.contour = deepcopy(contour) # Create copy of contour to be altered for visualization
        self.transformToPixmap()
        self.crop()
        self.scale()
        self.drawOnPixmap(pen)
        self.setPixmap(self.pixmap)
    def transformToPixmap(self):
        '''Transforms points from RECONSTRUCT'S coordsys to PySide's points'''
        # Convert biological points to pixel points
        self.contour.points = list(map(tuple, self.contour.transform._tform.inverse(np.asarray(self.contour.points) / self.image.mag)))
        # Is Pixmap valid?
        if self.pixmap.isNull(): # If image doesnt exist...
            # Get shape from contour to determine size of background
            minx,miny,maxx,maxy = self.contour.shape.bounds
            self.pixmap = QPixmap(maxx-minx+200,maxy-miny+200)
            self.pixmap.fill(fillColor=Qt.black)
        # Apply flip and translation to get points in PySide's image space
        flipVector = np.array( [1,-1] ) # Flip about x axis
        translationVector = np.array( [0,self.pixmap.size().height()] )
        transformedPoints = list(map(tuple,translationVector+(np.array(list(self.contour.shape.exterior.coords))*flipVector)))
        # Update self.contour's information to match transformation
        self.contour.points = transformedPoints
    def crop(self):
        '''Crops image.'''
        # Determine crop region
        minx,miny,maxx,maxy = self.contour.shape.bounds
        x = minx-100 # minimum x and L-padding
        y = miny-100 # minimum y and L-padding
        width = maxx-x+100 # width and R-padding
        height = maxy-y+100 # width and R-padding
        # Crop pixmap to fit shape (with padding as defined above)
        self.pixmap = self.pixmap.copy(x,y,width,height)
        # Adjust points to crop region
        cropVector = np.array( [x,y] )
        croppedPoints = list(map(tuple, np.array(self.contour.points)-cropVector ))
        self.contour.points = croppedPoints
    def scale(self):
        # Scale image
        preCropSize = self.pixmap.size()
        self.pixmap = self.pixmap.copy().scaled( 500, 500, Qt.KeepAspectRatio ) #=== is copy necessary?
        # Scale points
        preWidth = float(preCropSize.width())
        preHeight = float(preCropSize.height())
        # Prevent division by 0
        if preWidth == 0.0 or preHeight == 0.0:
            preWidth = 1.0
            preHeight = 1.0
        wScale = self.pixmap.size().width()/preWidth
        hScale = self.pixmap.size().height()/preHeight
        scale = np.array([wScale,hScale])
        scaledPoints = list(map(tuple,np.array(self.contour.points)*scale))
        self.contour.points = scaledPoints
    def drawOnPixmap(self, pen=Qt.red):
        # Create polygon to draw
        polygon = QPolygon()
        for point in self.contour.points:
            polygon.append( QPoint(*point) )
        # Draw polygon on pixmap
        painter = QPainter()
        painter.begin(self.pixmap)
        painter.setPen(pen)
        painter.drawConvexPolygon(polygon)
class resolveOvlp(QDialog):
    def __init__(self, item):
        QDialog.__init__(self)
        self.setWindowTitle('Contour Overlap Resolution')
        self.item = item
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
        self.exec_()
    def loadObjects(self):
        # Buttons to choose contours
        self.checkBoxes = []
        for i in range (0, self.item.numContours):
          setattr(self, 'contCheck'+str(i+1), QCheckBox('Choose Contour '+str(i+1)))
          (self.checkBoxes).append(getattr(self, 'contCheck'+str(i+1)))
#        for but in self.chooseButs:
#            but.setMinimumHeight(50)
        # Labels to hold pixmap
        self.doneContBut = QPushButton('Done') 
        self.doneContBut.setMinimumHeight(50)       
        self.pix1 = None
        self.pix2 = None
    def loadFunctions(self):
        for i in range (0, self.item.numContours):
          setattr(self, 'contCheck'+str(i+1), QCheckBox('Choose Contour '+str(i+1)))
          (self.checkBoxes).append(getattr(self, 'contCheck'+str(i+1)))

        for i in range (0, self.item.numContours):
          setattr(self, 'pix'+str(i+1), contourPixmap(getattr(self.item, 'image'+str(i+1)),getattr(self.item, 'contour'+str(i+1)), pen =Qt.white))

        self.doneContBut.clicked.connect(self.chosenContour)

    def loadLayout(self):
        container = QVBoxLayout() # Contains everything
        # - Contains Images
        imageContainer = QHBoxLayout()
        for i in range (0, self.item.numContours):
          imageContainer.addWidget(getattr(self, 'pix'+str(i+1)))
        # - Contains buttons
        butBox = QHBoxLayout()
        for i in range (0, self.item.numContours):
          butBox.addWidget(getattr(self, 'contCheck'+str(i+1)))
        # Add other containers to container
        butBox.addWidget(self.doneContBut)
        container.addLayout(imageContainer)
        container.addLayout(butBox)
        self.setLayout(container)

    def chosenContour(self):
        self.checkedContours = ""
        for i in range (0, self.item.numContours):
          if getattr(self, 'contCheck'+str(i+1)).isChecked():
            self.checkedContours += "1"
          else:
            self.checkedContours += "0"
        
        self.checkedContours = int(self.checkedContours)
        self.done(self.checkedContours)
     

#    def finish(self): # Return int associated with selected contour
#        for i in range (0, self.item.numContours):
#          if self.sender() == getattr(self, 'contCheck'+str(i+1)):
#            self.done([i+1])

class contourTableItem(QListWidgetItem):
    '''This class has the functionality of a QListWidgetItem while also being able to store a pointer to the contour(s) it represents.'''
    def __init__(self, contour, table, images):
        QListWidgetItem.__init__(self)
        if type(contour) == type([]): # Overlapping contours are in pairs
            self.contour = None
            self.numContours = len(contour)
            for i in range (0, len(contour)):
              setattr(self, 'contour'+str(i+1), contour[i])  
            if type(images) == type([]): # Images for conflict resolution
                for i in range (0, len(images)):                
                  setattr(self,'image'+str(i+1), images[i])
            self.setText(self.contour1.name)
            self.table = table
            self.resolved = False
        else:
            self.numContours = 1
            self.contour = [contour]
            self.image = [images[0]]
            self.setText(contour.name)
            self.table = table
            self.resolved = False
    def clicked(self):
        item = self
        a = QVBoxLayout() 
        if self.resolved or self.numContours==1: # single contour
            if self.resolved:
              pic = []
              for i in range(0,len(self.contour)):
                  pic.append(contourPixmap(self.image[i], self.contour[i]))
              for img in pic:
                a.addWidget(img)
            else:
              pic = contourPixmap(self.image[0], self.contour[0])
              a.addWidget(pic)
            
            dia = QDialog()
            dia.setLayout(a)
            dia.exec_()
        else: # Conflicting or overlapping
            msg = resolveOvlp(item)
            resolution = str(msg.result())
            count = 1
            self.contour = []
            self.image = []
            self.resolved = True
            for ch in resolution:
              if ch == "1":
                self.contour.append(getattr(self, 'contour'+str(count)))
                self.image.append(getattr(self, 'image'+str(count)))
              count += 1

            self.setBackground(QColor('lightgreen'))          

          
    def forceResolution(self, integer):
        if int(integer) == 1:
            self.contour = self.contour1
        elif int(integer) == 2:
            self.contour = self.contour2
        elif int(integer) == 3:
            self.contour = [self.contour1, self.contour2]

        else:
            print ('Invalid entry')
            return
        self.setBackground(QColor('lightgreen'))
