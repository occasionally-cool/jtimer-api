"""sqlalchemy models for flask application"""

import operator
from enum import IntEnum
from passlib.hash import bcrypt
from sqlalchemy import func, or_, desc, literal_column

from jtimer.extensions import db
from jtimer.points import calc_points


class Player(db.Model):
    """Player table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    steam_id = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(32), nullable=False)
    country = db.Column(db.String(2), nullable=False)
    s_points = db.Column(db.Integer, default=0, nullable=False)
    d_points = db.Column(db.Integer, default=0, nullable=False)
    s_rank = db.Column(db.Integer, default=0, nullable=False)
    d_rank = db.Column(db.Integer, default=0, nullable=False)

    @property
    def json(self):
        """Json serializable dictionary of the model"""
        return {
            "id": self.id_,
            "steam_id": self.steam_id,
            "name": self.username,
            "country": self.country,
            "rank_info": {
                "soldier_points": self.s_points,
                "demo_points": self.d_points,
                "soldier_rank": self.s_rank,
                "demoman_rank": self.d_rank,
            },
        }

    def add(self):
        """Adds the model to the sqlalchemy session and commits.
        Updates the existing model if it already exists in the database."""
        query = Player.query.filter_by(id_=self.id_).first()
        if not query:
            db.session.add(self)

        db.session.commit()

    @staticmethod
    def calculate_ranks():
        """Calculate player ranks and points"""

        # Get points from MapTimes
        soldier_points = (
            MapTimes.query.with_entities(
                MapTimes.player_id, func.sum(MapTimes.points).label("points")
            )
            .filter(MapTimes.player_class == 2)
            .group_by(MapTimes.player_id)
            .filter(literal_column("points") > 0)
            .order_by(desc(literal_column("points")))
            .all()
        )
        if soldier_points is None:
            return

        demoman_points = (
            MapTimes.query.with_entities(
                MapTimes.player_id, func.sum(MapTimes.points).label("points")
            )
            .filter(MapTimes.player_class == 4)
            .group_by(MapTimes.player_id)
            .filter(literal_column("points") > 0)
            .order_by(desc(literal_column("points")))
            .all()
        )
        if demoman_points is None:
            return

        # Get players
        players = Player.query.all()
        if players is None:
            return

        # Update soldier ranks and points
        for i in range(0, len(soldier_points)):
            for player in players:
                if player.id_ == soldier_points[i].player_id:
                    player.s_points = soldier_points[i].points
                    player.s_rank = i + 1
                    break

        # Update demoman ranks and points
        for i in range(0, len(demoman_points)):
            for player in players:
                if player.id_ == demoman_points[i].player_id:
                    player.d_points = demoman_points[i].points
                    player.d_rank = i + 1
                    break

        db.session.commit()


class Zone(db.Model):
    """Zone table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    x1 = db.Column(db.Integer, nullable=False)
    y1 = db.Column(db.Integer, nullable=False)
    z1 = db.Column(db.Integer, nullable=False)
    x2 = db.Column(db.Integer, nullable=False)
    y2 = db.Column(db.Integer, nullable=False)
    z2 = db.Column(db.Integer, nullable=False)
    orientation = db.Column(db.Integer, default=0)

    @property
    def json(self):
        """Json serializable dictionary of the model"""
        return {
            "id": self.id_,
            "p1": [self.x1, self.y1, self.z1],
            "p2": [self.x2, self.y2, self.z2],
            "orientation": self.orientation,
        }

    def add(self):
        """Adds the model to the sqlalchemy session and commits.
        Updates the existing model if it already exists in the database."""
        query = Zone.query.filter_by(id_=self.id_).first()
        if not query:
            db.session.add(self)

        db.session.commit()


class Map(db.Model):
    """Map table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    mapname = db.Column(db.String(128), nullable=False)
    stier = db.Column(db.Integer, default=0, nullable=False)
    dtier = db.Column(db.Integer, default=0, nullable=False)
    s_completions = db.Column(db.Integer, default=0, nullable=False)
    d_completions = db.Column(db.Integer, default=0, nullable=False)
    start_zone = db.Column(None, db.ForeignKey("zone.id"), default=None)
    end_zone = db.Column(None, db.ForeignKey("zone.id"), default=None)

    @property
    def json(self):
        """Json serializable dictionary of the model"""
        return {
            "id": self.id_,
            "name": self.mapname,
            "tiers": {"soldier": self.stier, "demoman": self.dtier},
            "completions": {
                "soldier": self.s_completions,
                "demoman": self.d_completions,
            },
        }

    def add(self):
        """Adds the model to the sqlalchemy session and commits.
        Updates the existing model if it already exists in the database."""
        query = Map.query.filter(
            Map.mapname == self.mapname or Map.id_ == self.id_
        ).first()
        if not query:
            db.session.add(self)

        db.session.commit()


class Author(db.Model):
    """Author table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    player_id = db.Column(None, db.ForeignKey("player.id"), nullable=True)
    map_id = db.Column(None, db.ForeignKey("map.id"), nullable=False)

    @property
    def json(self):
        """Json serializable dictionary of the model"""
        player = Player.query.filter_by(id_=self.player_id).first()
        if player:
            player_dict = player.json
            del player_dict["rank_info"]
            player_dict["name"] = self.name
            return player_dict

        return {"name": self.name}


class Course(db.Model):
    """Course table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    map_id = db.Column(None, db.ForeignKey("map.id"), nullable=False)
    course_index = db.Column(db.Integer, nullable=False)
    stier = db.Column(db.Integer, default=0, nullable=False)
    dtier = db.Column(db.Integer, default=0, nullable=False)
    s_completions = db.Column(db.Integer, default=0, nullable=False)
    d_completions = db.Column(db.Integer, default=0, nullable=False)
    start_zone = db.Column(None, db.ForeignKey("zone.id"), default=None)
    end_zone = db.Column(None, db.ForeignKey("zone.id"), default=None)


class Bonus(db.Model):
    """Bonus table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    map_id = db.Column(None, db.ForeignKey("map.id"), nullable=False)
    bonus_index = db.Column(db.Integer, nullable=False)
    stier = db.Column(db.Integer, default=0, nullable=False)
    dtier = db.Column(db.Integer, default=0, nullable=False)
    s_completions = db.Column(db.Integer, default=0, nullable=False)
    d_completions = db.Column(db.Integer, default=0, nullable=False)
    start_zone = db.Column(None, db.ForeignKey("zone.id"), default=None)
    end_zone = db.Column(None, db.ForeignKey("zone.id"), default=None)


class MapCheckpoint(db.Model):
    """map_checkpoint table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    zone_id = db.Column(None, db.ForeignKey("zone.id"), nullable=False)
    map_id = db.Column(None, db.ForeignKey("map.id"), nullable=False)
    cp_index = db.Column(db.Integer, nullable=False)

    @property
    def json(self):
        """Json serializable dictionary of the model"""
        zone = Zone.query.filter_by(id_=self.zone_id).first()
        zone_dict = None
        if zone:
            zone_dict = zone.json

        return {
            "id": self.id_,
            "zone_type": "cp",
            "map_id": self.map_id,
            "cp_index": self.cp_index,
            "zone": zone_dict,
        }

    def add(self):
        """Adds the model to the sqlalchemy session and commits.
        Updates the existing model if it already exists in the database."""
        query = MapCheckpoint.query.filter_by(id_=self.id_).first()
        if not query:
            db.session.add(self)
        db.session.commit()


class CourseCheckpoint(db.Model):
    """course_checkpoint table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    zone_id = db.Column(None, db.ForeignKey("zone.id"), nullable=False)
    course_id = db.Column(None, db.ForeignKey("course.id"), nullable=False)
    cp_index = db.Column(db.Integer, nullable=False)


class BonusCheckpoint(db.Model):
    """bonus_checkpoint table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    zone_id = db.Column(None, db.ForeignKey("zone.id"), nullable=False)
    bonus_id = db.Column(None, db.ForeignKey("bonus.id"), nullable=False)
    cp_index = db.Column(db.Integer, nullable=False)


class MapTimes(db.Model):
    """map_times table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    map_id = db.Column(None, db.ForeignKey("map.id"), nullable=False)
    player_id = db.Column(None, db.ForeignKey("player.id"), nullable=False)
    player_class = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Float(precision=53), nullable=False)
    end_time = db.Column(db.Float(precision=53), nullable=False)
    duration = db.Column(db.Float(precision=53), nullable=False)
    rank = db.Column(db.Integer, nullable=True)
    points = db.Column(db.Integer, nullable=True)

    @property
    def json(self):
        """Json serializable dictionary of the model"""
        player = Player.query.filter_by(id_=self.player_id).first()
        player_json = None
        if player is not None:
            player_json = player.json
        checkpoints = self.get_checkpoint_times()

        return {
            "id": self.id_,
            "map_id": self.map_id,
            "player": player_json,
            "class": self.player_class,
            "time": self.end_time - self.start_time,
            "rank": self.rank,
            "checkpoints": checkpoints,
        }

    def get_checkpoint_times(self):
        checkpoint_times = MapCheckpointTimes.query.filter_by(time_id=self.id_).all()
        checkpoint_times_json = []
        if checkpoint_times is not None:
            for checkpoint_time in checkpoint_times:
                map_checkpoint = MapCheckpoint.query.filter_by(
                    id_=checkpoint_time.checkpoint_id
                ).first()
                if map_checkpoint is not None:
                    checkpoint_times_json.append(checkpoint_time.json)
                    checkpoint_times_json[-1]["cp_index"] = map_checkpoint.cp_index
                    checkpoint_times_json[-1]["time"] -= self.start_time

        return checkpoint_times_json

    def add(self, checkpoints=[]):
        """Adds the model to the sqlalchemy session and commits.
        Updates the existing model if it already exists in the database.
        Existing time is only updated if the new one is faster."""
        query = MapTimes.query.filter(
            MapTimes.map_id == self.map_id
            and MapTimes.player_id == self.player_id
            and MapTimes.player_class == self.player_class
        ).first()

        records = MapTimes.get_records(self.map_id)

        if not bool(query):
            # no existing run, add this
            db.session.add(self)

            # add new checkpoints
            for checkpoint in checkpoints:
                map_checkpoint = MapCheckpoint.query.filter_by(
                    map_id=self.map_id, cp_index=checkpoint["cp_index"]
                ).first()
                if map_checkpoint is not None:
                    map_checkpoint_time = MapCheckpointTimes(
                        checkpoint_id=map_checkpoint.id_,
                        time_id=self.id_,
                        time=checkpoint["time"],
                    )
                    db.session.add(map_checkpoint_time)

            db.session.commit()

            # update ranks
            completions = MapTimes.update_ranks(self.map_id)

            return {
                "result": InsertResult.ADDED,
                "rank": self.rank,
                "completions": completions,
                "points_gained": self.points,
                "duration": self.duration,
                "records": records,
            }

        # time already exists, check if faster
        old_time = query.end_time - query.start_time
        new_time = self.end_time - self.start_time
        old_points = query.points

        if new_time < old_time:
            improvement = old_time - new_time

            # faster, add this
            db.session.add(self)

            # add new checkpoints
            for checkpoint in checkpoints:
                map_checkpoint = MapCheckpoint.query.filter_by(
                    map_id=self.map_id, cp_index=checkpoint["cp_index"]
                ).first()
                if map_checkpoint is not None:
                    map_checkpoint_time = MapCheckpointTimes(
                        checkpoint_id=map_checkpoint.id_,
                        time_id=self.id_,
                        time=checkpoint["time"],
                    )
                    db.session.add(map_checkpoint_time)

            # remove old checkpoints
            old_checkpoints = MapCheckpointTimes.query.filter_by(
                time_id=query.id_
            ).all()
            if old_checkpoints is not None:
                for old_checkpoint in old_checkpoints:
                    db.session.delete(old_checkpoint)

                # have to commit checkpoint deletions first
                # to avoid foreign key constraint errors
                db.session.commit()

            # remove old time
            db.session.delete(query)
            db.session.commit()

            # update ranks
            completions = MapTimes.update_ranks(self.map_id)

            if self.rank == 1:
                # separate old records if time is new record
                new_records = records.copy()
                if self.player_class == 2:
                    new_records["soldier"] = self.json
                elif self.player_class == 4:
                    new_records["demoman"] = self.json
                return {
                    "result": InsertResult.UPDATED,
                    "rank": self.rank,
                    "points_gained": self.points - old_points,
                    "completions": completions,
                    "improvement": improvement,
                    "duration": self.duration,
                    "records": new_records,
                    "old_records": records,
                }

            return {
                "result": InsertResult.UPDATED,
                "rank": self.rank,
                "points_gained": self.points - old_points,
                "completions": completions,
                "improvement": improvement,
                "duration": self.duration,
                "records": records,
            }

        # slower
        return {
            "result": InsertResult.NONE,
            "duration": self.duration,
            "records": records,
            "old_time": old_time,
        }

    @staticmethod
    def get_records(map_id):
        """Get map record for both classes."""
        swr = (
            MapTimes.query.filter(MapTimes.map_id == map_id, MapTimes.player_class == 2)
            .order_by(MapTimes.duration)
            .first()
        )
        dwr = (
            MapTimes.query.filter(MapTimes.map_id == map_id, MapTimes.player_class == 4)
            .order_by(MapTimes.duration)
            .first()
        )
        swr_json = None
        if swr is not None:
            swr_json = swr.json
        dwr_json = None
        if dwr is not None:
            dwr_json = dwr.json
        return {"soldier": swr_json, "demoman": dwr_json}

    @staticmethod
    def update_ranks(map_id):
        """Update ranks and points for all times on map."""
        completions = {"soldier": 0, "demoman": 0}

        soldier_times = (
            MapTimes.query.filter(MapTimes.map_id == map_id, MapTimes.player_class == 2)
            .order_by(MapTimes.duration)
            .all()
        )
        if soldier_times:
            completions["soldier"] = len(soldier_times)
            for i in range(0, len(soldier_times)):
                soldier_times[i].rank = i + 1
                soldier_times[i].points = calc_points(
                    soldier_times[0].duration,
                    soldier_times[i].duration,
                    len(soldier_times),
                )

        demo_times = (
            MapTimes.query.filter(MapTimes.map_id == map_id, MapTimes.player_class == 4)
            .order_by(MapTimes.duration)
            .all()
        )
        if demo_times:
            completions["demoman"] = len(demo_times)
            for i in range(0, len(demo_times)):
                demo_times[i].rank = i + 1
                demo_times[i].points = calc_points(
                    demo_times[0].duration, demo_times[i].duration, len(demo_times)
                )

        db.session.commit()

        # Update player ranks and points
        Player.calculate_ranks()

        return completions


class CourseTimes(db.Model):
    """course_times table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    course_id = db.Column(None, db.ForeignKey("course.id"), nullable=False)
    player_id = db.Column(None, db.ForeignKey("player.id"), nullable=False)
    player_class = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Float(precision=53), nullable=False)
    end_time = db.Column(db.Float(precision=53), nullable=False)
    rank = db.Column(db.Integer, nullable=False)


class BonusTimes(db.Model):
    """bonus_times table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    bonus_id = db.Column(None, db.ForeignKey("bonus.id"), nullable=False)
    player_id = db.Column(None, db.ForeignKey("player.id"), nullable=False)
    player_class = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Float(precision=53), nullable=False)
    end_time = db.Column(db.Float(precision=53), nullable=False)
    rank = db.Column(db.Integer, nullable=False)


class MapCheckpointTimes(db.Model):
    """map_checkpoint_times table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    checkpoint_id = db.Column(None, db.ForeignKey("map_checkpoint.id"), nullable=False)
    time_id = db.Column(None, db.ForeignKey("map_times.id"), nullable=False)
    time = db.Column(db.Float(precision=53), nullable=False)

    def get_map_checkpoint(self):
        query = MapCheckpoint.query.filter_by(id_=checkpoint_id).first()
        return query

    @property
    def json(self):
        """Json serializable dictionary of the model"""
        return {"id": self.checkpoint_id, "time": self.time}


class CourseCheckpointTimes(db.Model):
    """course_checkpoint_times table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    checkpoint_id = db.Column(
        None, db.ForeignKey("course_checkpoint.id"), nullable=False
    )
    time_id = db.Column(None, db.ForeignKey("course_times.id"), nullable=False)
    time = db.Column(db.Float(precision=53), nullable=False)


class BonusCheckpointTimes(db.Model):
    """bonus_checkpoint_times table sqlalchemy model"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    checkpoint_id = db.Column(
        None, db.ForeignKey("bonus_checkpoint.id"), nullable=False
    )
    time_id = db.Column(None, db.ForeignKey("bonus_times.id"), nullable=False)
    time = db.Column(db.Float(precision=53), nullable=False)


class User(db.Model):
    """user table sqlalchemy model
    for authenticating restricted views"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    username = db.Column("username", db.String(64), nullable=False)
    password = db.Column("password", db.String(256), nullable=False)

    @staticmethod
    def generate_hash(password):
        """Returns a new hash for the password."""
        return bcrypt.hash(password)

    def verify_hash(self, password):
        """Checks password against stored password hash of the user.
        Returns bool."""
        return bcrypt.verify(password, self.password)

    def change_hash(self, password):
        """Changes stored password hash of the user."""
        self.password = self.generate_hash(password)
        db.session.commit()

    def add(self):
        """Adds the model to the sqlalchemy session and commits.
        Updates the existing model if it already exists in the database."""
        query = User.query.filter_by(username=self.username).first()
        if not bool(query):
            db.session.add(self)
        db.session.commit()


class RevokedToken(db.Model):
    """revoked_token table sqlalchemy model
    for storing revoked tokens"""

    id_ = db.Column("id", db.Integer, primary_key=True)
    jti = db.Column("jti", db.String(120), nullable=False)

    def add(self):
        """Adds the model to the sqlalchemy session and commits."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def is_jti_blacklisted(cls, jti):
        """Checks if token 'jti' is blacklisted.
        Returns bool."""
        query = cls.query.filter_by(jti=jti).first()
        return bool(query)


class InsertResult(IntEnum):
    """Result of insert query.
    Used for responding to api requests."""

    NONE = 0
    ADDED = 1
    UPDATED = 2
